import fs from "node:fs";
import { Wallet } from "file:///C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer/node_modules/ethers/lib.esm/index.js";
import {
  chains,
  createAccount,
  createClient,
} from "file:///C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer/node_modules/genlayer-js/dist/index.js";

const secretsRaw = fs
  .readFileSync("../visual-state-gate/.deploy-secrets.json", "utf8")
  .replace(/^\uFEFF/, "");
const secrets = JSON.parse(secretsRaw);
const keystore = fs.readFileSync(
  `C:/Users/DELL/.genlayer/keystores/${secrets.account}.json`,
  "utf8",
);
const wallet = await Wallet.fromEncryptedJson(keystore, secrets.password);
const account = createAccount(wallet.privateKey);
const client = createClient({ chain: chains.studionet, account });

const code = fs.readFileSync("contracts/agent_mandate_firewall.py", "utf8");
const zero = "0x0000000000000000000000000000000000000000";
const addr = account.address;
const evidenceUrl =
  "https://raw.githubusercontent.com/Ifem1/Agent-Mandate-Firewall/main/evidence/example-domain-payment.txt";

async function wait(hash, label, retries = 90) {
  const receipt = await client.waitForTransactionReceipt({
    hash,
    status: "ACCEPTED",
    interval: 5000,
    retries,
  });
  console.log(label, JSON.stringify({
    hash,
    status: receipt.status_name,
    result: receipt.result_name,
    contractAddress: receipt.contract_address ?? receipt.contractAddress ?? null,
  }));
  return receipt;
}

async function write(address, functionName, args, value = 0n, retries = 90) {
  const hash = await client.writeContract({
    account,
    address,
    functionName,
    args,
    value,
    consensusMaxRotations: 3,
  });
  await wait(hash, functionName, retries);
  return hash;
}

console.log("account", addr);
const deployHash = await client.deployContract({
  account,
  code,
  args: [1000, 5000, 1, 900, 360, 320, 500],
  consensusMaxRotations: 3,
});
const deployReceipt = await wait(deployHash, "deploy", 120);
const contract =
  deployReceipt.contract_address ??
  deployReceipt.contractAddress ??
  deployReceipt.data?.contract_address ??
  deployReceipt.data?.contractAddress;
if (!contract) {
  console.log("deploy receipt keys", Object.keys(deployReceipt));
  throw new Error("could not find deployed contract address in receipt");
}

const policy =
  "Allow tiny payments for public web documentation checks when the public evidence identifies the service, exact amount, recipient address, and purpose.";

const openHash = await write(contract, "open_mandate", [addr, policy, 5, zero], 10n);
const mandateId = "amf-m-1";
console.log("mandate", JSON.stringify(await client.readContract({
  address: contract,
  functionName: "get_mandate",
  args: [mandateId],
}), null, 2));

const fundHash = await write(contract, "fund_mandate", [mandateId], 5n);
const pauseHash = await write(contract, "pause_mandate", [mandateId]);
const resumeHash = await write(contract, "resume_mandate", [mandateId]);

const requestHash = await write(contract, "request_payment", [
  mandateId,
  1,
  addr,
  "Pay for Example Domain documentation verification.",
  evidenceUrl,
  "live-example-domain",
]);
const paymentId = await client.readContract({
  address: contract,
  functionName: "latest_payment_for",
  args: ["live-example-domain"],
});
console.log("paymentId", paymentId);
console.log("afterRequest", JSON.stringify(await client.readContract({
  address: contract,
  functionName: "get_payment",
  args: [paymentId],
}), null, 2));

const resolveHash = await write(contract, "resolve_payment", [paymentId], 0n, 120);
const afterResolve = await client.readContract({
  address: contract,
  functionName: "get_payment",
  args: [paymentId],
});
console.log("afterResolve", JSON.stringify(afterResolve, null, 2));

let withdrawHash = "";
const withdrawable = await client.readContract({
  address: contract,
  functionName: "withdrawable",
  args: [paymentId, addr],
});
console.log("withdrawable", withdrawable?.toString?.() ?? withdrawable);
if ((withdrawable?.toString?.() ?? String(withdrawable)) !== "0") {
  withdrawHash = await write(contract, "withdraw", [paymentId]);
}

const reclaimHash = await write(contract, "reclaim_available", [mandateId, 1]);
const finalMandate = await client.readContract({
  address: contract,
  functionName: "get_mandate",
  args: [mandateId],
});
const finalPayment = await client.readContract({
  address: contract,
  functionName: "get_payment",
  args: [paymentId],
});
const config = await client.readContract({
  address: contract,
  functionName: "get_config",
  args: [],
});

console.log("summary", JSON.stringify({
  contract,
  deployHash,
  openHash,
  fundHash,
  pauseHash,
  resumeHash,
  requestHash,
  resolveHash,
  withdrawHash,
  reclaimHash,
  mandateId,
  paymentId,
  finalStatus: finalPayment.status,
  finalPayment,
  finalMandate,
  config,
}, null, 2));
