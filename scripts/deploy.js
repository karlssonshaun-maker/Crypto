/**
 * IGNIS (IGN) deployment script.
 *
 * Usage:
 *   npm run deploy:local      — local Hardhat node
 *   npm run deploy:sepolia    — Ethereum Sepolia testnet
 *   npm run deploy:bsc        — BNB Smart Chain testnet
 *
 * After deployment, verify on a block explorer with:
 *   npx hardhat verify --network <network> <CONTRACT_ADDRESS> <TREASURY_ADDRESS>
 */

const { ethers, network } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();

  console.log("=".repeat(60));
  console.log("  IGNIS (IGN) — Deployment");
  console.log("=".repeat(60));
  console.log(`  Network    : ${network.name}`);
  console.log(`  Deployer   : ${deployer.address}`);

  const balance = await ethers.provider.getBalance(deployer.address);
  console.log(`  Balance    : ${ethers.formatEther(balance)} ETH/BNB`);

  // Treasury receives the 3% fee on every transfer.
  // Default = deployer. Change TREASURY_ADDRESS in .env for production.
  const treasuryAddress =
    process.env.TREASURY_ADDRESS && process.env.TREASURY_ADDRESS !== ""
      ? process.env.TREASURY_ADDRESS
      : deployer.address;

  console.log(`  Treasury   : ${treasuryAddress}`);
  console.log("-".repeat(60));

  const IGNIS = await ethers.getContractFactory("IGNIS");
  console.log("  Deploying contract...");

  const ignis = await IGNIS.deploy(treasuryAddress);
  await ignis.waitForDeployment();

  const address      = await ignis.getAddress();
  const totalSupply  = await ignis.totalSupply();
  const phase        = await ignis.currentPhaseName();
  const burnRate     = await ignis.currentBurnRate();

  console.log("=".repeat(60));
  console.log(`  Contract   : ${address}`);
  console.log(`  Supply     : ${ethers.formatEther(totalSupply)} IGN`);
  console.log(`  Phase      : ${phase}  (burn ${burnRate}% per tx)`);
  console.log("=".repeat(60));
  console.log();
  console.log("  To verify on block explorer:");
  console.log(`  npx hardhat verify --network ${network.name} ${address} ${treasuryAddress}`);
  console.log();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
