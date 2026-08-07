import fs from "node:fs";
import { Wallet } from "file:///C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer/node_modules/ethers/lib.esm/index.js";
import {
  chains,
  createAccount,
  createClient,
} from "file:///C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer/node_modules/genlayer-js/dist/index.js";

const secretsRaw = fs.readFileSync(".amf-deploy-secrets.json", "utf8").replace(/^\uFEFF/, "");
const secrets = JSON.parse(secretsRaw);
const keystore = fs.readFileSync(`C:/Users/DELL/.genlayer/keystores/${secrets.account}.json`, "utf8");
const wallet = await Wallet.fromEncryptedJson(keystore, secrets.password);
const account = createAccount(wallet.privateKey);
const client = createClient({ chain: chains.studionet, account });

const contract = "0xD5259E2c6e2D0433e47d775769085de3A09ADc4c";
const addr = account.address;
const mandateId = "amf-m-1";
const paymentId = "amf-p-1";

async function wait(hash, label, retries = 120) {
  const receipt = await client.waitForTransactionReceipt({ hash, status: "ACCEPTED", interval: 5000, retries });
  console.log(label, JSON.stringify({ hash, status: receipt.status_name, result: receipt.result_name }));
  return receipt;
}
async function write(functionName, args, value = 0n, retries = 120) {
  const hash = await client.writeContract({ account, address: contract, functionName, args, value, consensusMaxRotations: 3 });
  return wait(hash, functionName, retries);
}

// Check current state
const pmt = await client.readContract({ address: contract, functionName: "get_payment", args: [paymentId] });
console.log("currentPayment", JSON.stringify(pmt, null, 2));

const mnd = await client.readContract({ address: contract, functionName: "get_mandate", args: [mandateId] });
console.log("currentMandate", JSON.stringify(mnd, null, 2));

// retry resolve_payment if still PENDING
let finalStatus = pmt.status;
let resolveHash2 = "";
if (pmt.status === "PENDING") {
  const r = await write("resolve_payment", [paymentId], 0n, 120);
  resolveHash2 = r.hash ?? "";
  const after = await client.readContract({ address: contract, functionName: "get_payment", args: [paymentId] });
  console.log("afterResolve2", JSON.stringify(after, null, 2));
  finalStatus = after.status;
}

// withdraw if approved
let withdrawHash = "";
if (finalStatus === "APPROVED") {
  const w = await write("withdraw", [paymentId]);
  withdrawHash = w.hash ?? "";
}

// reclaim 1 wei of available funds
let reclaimHash = "";
try {
  const r = await write("reclaim_available", [mandateId, 1]);
  reclaimHash = r.hash ?? "";
} catch(e) {
  console.log("reclaim skipped:", e.message?.slice(0, 80));
}

// Final reads
const cfg = await client.readContract({ address: contract, functionName: "get_config", args: [] });
const finalPmt = await client.readContract({ address: contract, functionName: "get_payment", args: [paymentId] });
const finalMnd = await client.readContract({ address: contract, functionName: "get_mandate", args: [mandateId] });
const mStatus = await client.readContract({ address: contract, functionName: "mandate_status", args: [mandateId] });
const pStatus = await client.readContract({ address: contract, functionName: "payment_status", args: [paymentId] });
const latestKey = await client.readContract({ address: contract, functionName: "latest_payment_for", args: [mandateId, "live-example-domain"] });
const wdable = await client.readContract({ address: contract, functionName: "withdrawable", args: [paymentId, addr] });

console.log("FINAL_SUMMARY", JSON.stringify({
  contract,
  mandateId, paymentId,
  resolveHash2, withdrawHash, reclaimHash,
  latestKeyResolves: latestKey,
  mandateStatus: mStatus,
  paymentStatus: pStatus,
  withdrawable: wdable?.toString(),
  finalPaymentStatus: finalPmt.status,
  finalPayment: finalPmt,
  finalMandate: finalMnd,
  config: cfg,
}, null, 2));
