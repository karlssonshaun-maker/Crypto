require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

const PRIVATE_KEY  = process.env.PRIVATE_KEY  || "0x" + "0".repeat(64);
const RPC_URL      = process.env.RPC_URL       || "";
const ETHERSCAN_KEY = process.env.ETHERSCAN_API_KEY || "";
const BSCSCAN_KEY   = process.env.BSCSCAN_API_KEY  || "";

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: { enabled: true, runs: 200 },
    },
  },

  networks: {
    // Local Hardhat node  →  npm run node  then  npm run deploy:local
    localhost: {
      url: "http://127.0.0.1:8545",
    },

    // Ethereum Sepolia testnet  (get free ETH at sepoliafaucet.com)
    sepolia: {
      url: RPC_URL || "https://rpc.sepolia.org",
      accounts: [PRIVATE_KEY],
      chainId: 11155111,
    },

    // BNB Smart Chain testnet  (get free BNB at testnet.bnbchain.org/faucet-smart)
    bscTestnet: {
      url: "https://data-seed-prebsc-1-s1.binance.org:8545/",
      accounts: [PRIVATE_KEY],
      chainId: 97,
    },
  },

  etherscan: {
    apiKey: {
      sepolia:    ETHERSCAN_KEY,
      bscTestnet: BSCSCAN_KEY,
    },
    customChains: [
      {
        network: "bscTestnet",
        chainId: 97,
        urls: {
          apiURL:    "https://api-testnet.bscscan.com/api",
          browserURL: "https://testnet.bscscan.com",
        },
      },
    ],
  },
};
