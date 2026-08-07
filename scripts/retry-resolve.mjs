import fs from "node:fs";
import { Wallet } from "file:///C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer/node_modules/ethers/lib.esm/index.js";
import {
  chains,
  createAccount,
  createClient,
} from "file:///C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer/node_modules/genlayer-js/dist/index.js";

const secrets = JSON.parse(fs.readFileSync(".amf-deploy-secrets.json", "utf8").replace(/^\uFEFF/, ""));
const keystore = fs.readFileSync(`C:/Users/DELL/.genlayer/keystores/${secrets.account}.json`, "utf8");
const wallet = await Wallet.fromEncryptedJson(keystore, secrets.password);
const account = createAccount(wallet.privateKey);
const client = createClient({ chain: chains.studionet, account });

const contract = "0xD5259E2c6e2D0433e47d775769085de3A09ADc4c";
const paymentId = "amf-p-1";
const mandateId = "amf-m-1";
const addr = account.address;

// Try resolve up to 4 times
for (let i = 0; i < 4; i++) {
  const pmt = await client.readContract({ address: contract, functionName: "get_payment", args: [paymentId] });
  console.log(`attempt ${i+1} — status: ${pmt.status} attempts: ${pmt.attempts}`);
  if (pmt.status !== "PENDING") { console.log("terminal:", pmt.status); break; }

  const hash = await client.writeContract({
    account, address: contract,
    functionName: "resolve_payment",
    args: [paymentId],
    value: 0n,
    consensusMaxRotations: 5,
  });
  console.log("hash", hash);
  const receipt = await client.waitForTransactionReceipt({ hash, status: "ACCEPTED", interval: 6000, retries: 150 });
  console.log("result", receipt.result_name, "status", receipt.status_name);
  const after = await client.readContract({ address: contract, functionName: "get_payment", args: [paymentId] });
  console.log("after:", JSON.stringify({ status: after.status, confidence: after.confidence, approved_amount: after.approved_amount, attempts: after.attempts }));
  if (after.status !== "PENDING") {
    // if approved, withdraw
    if (after.status === "APPROVED") {
      const wh = await client.writeContract({ account, address: contract, functionName: "withdraw", args: [paymentId], value: 0n });
      const wr = await client.waitForTransactionReceipt({ hash: wh, status: "ACCEPTED", interval: 5000, retries: 90 });
      console.log("withdraw", wr.result_name, "hash", wh);
      const final = await client.readContract({ address: contract, functionName: "get_payment", args: [paymentId] });
      console.log("finalAfterWithdraw", JSON.stringify(final));
    }
    break;
  }
}
