"""
Next-Generation Cryptocurrency Deposit System
Supports: BTC, LTC, ETH, TON, DOGE, TRX, BNB, POL, SOL, and USDT (multiple chains)
Features:
- Temporary deposit addresses (1 hour)
- Live blockchain monitoring
- Real-time price tracking and balance updates
- Multi-chain USDT support (BEP20, ERC20, TRC20, SOL, TON)
- Advanced HD wallet derivation
"""

import logging
import asyncio
import json
import os
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
import httpx
from web3 import Web3
from eth_account import Account
from bip_utils import Bip44, Bip44Coins, Bip44Changes
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

# ==================== CONFIGURATION SECTION ====================
# FILL THESE MANUALLY - Leave blank if not available

# Master Private Keys (one per blockchain family)
MASTER_PRIVATE_KEY_BTC = "L4EvH9hcT8QxYNviNpwrqpKrerdrhjk8KPqqsvegKn2wrxfMfCaN"  # Bitcoin master private key (WIF or hex)
MASTER_PRIVATE_KEY_LTC = "L4EvH9hcT8QxYNviNpwrqpKrerdrhjk8KPqqsvegKn2wrxfMfCaN"  # Litecoin master private key
MASTER_PRIVATE_KEY_ETH = "d17bc5f695d66a8f8e6e336990fa96a75699914264bc2465c47bc5c3f6c3cf37"  # Ethereum master private key (for ETH, USDT-ERC20, POL)
MASTER_PRIVATE_KEY_BNB = "d17bc5f695d66a8f8e6e336990fa96a75699914264bc2465c47bc5c3f6c3cf37"  # Binance Smart Chain master private key (for BNB, USDT-BEP20)
MASTER_PRIVATE_KEY_SOL = "C3umDy13dNK7NjgF2eAEgxXfqa5cT2x7c3k6HVXTecBcx23MKe6h2LexSG1z1hFYQNJXFHPUc1rTDCX4xvkJVqi"  # Solana master private key (for SOL, USDT-SOL)
MASTER_PRIVATE_KEY_TON = "09877c9565fa71da4566254f8cf3114cc4a91c182aba23a8da36cc8dfc2e37c1"  # Toncoin master private key (for TON, USDT-TON)
MASTER_PRIVATE_KEY_DOGE = "L4EvH9hcT8QxYNviNpwrqpKrerdrhjk8KPqqsvegKn2wrxfMfCaN"  # Dogecoin master private key
MASTER_PRIVATE_KEY_TRX = "d17bc5f695d66a8f8e6e336990fa96a75699914264bc2465c47bc5c3f6c3cf37"  # Tron master private key (for TRX, USDT-TRC20)

# Central receiving wallet addresses (where funds are swept to)
CENTRAL_WALLET_ADDRESS_BTC = "bc1qt2gxcp90z5kve8y6wfyfxmafkl8e03x7phsmwu"
CENTRAL_WALLET_ADDRESS_LTC = "ltc1qwlzauf929r88lxw9y4znxs6aqhjk79vg8pz02e"
CENTRAL_WALLET_ADDRESS_ETH = "0x3011d124812d638c3eb4743ebe2261a2b0e47806"
CENTRAL_WALLET_ADDRESS_BNB = "0x3011d124812d638c3eb4743ebe2261a2b0e47806"
CENTRAL_WALLET_ADDRESS_SOL = "8DKPQrMr4X9gbbmZAcJXeLx1qHicrvLjBpRZDX1S4kgC"
CENTRAL_WALLET_ADDRESS_TON = "UQC2CsdJrFkX6MctJmyrfFPZZk1orq0ewjR6k2Zv7NNs8Mmi"
CENTRAL_WALLET_ADDRESS_DOGE = "D67DzsgV8i9ezi6BfNBe1KofMho8RRirME"
CENTRAL_WALLET_ADDRESS_TRX = "TDdSwtm4wz1147GbtXEmL8Ck3wDe7m95tu"

# Blockchain API Keys for monitoring deposits
BLOCKCYPHER_API_KEY = "cadd7a2c159d4440a1c9c8ce07b85a26"  # For BTC, LTC, DOGE - Get from https://www.blockcypher.com/
ETHERSCAN_API_KEY = "PGPXGH4Z6GAM71J7K3IMYN7M3JMN7IIR6F"  # For ETH, USDT-ERC20 - Get from https://etherscan.io/apis
BSCSCAN_API_KEY = "PGPXGH4Z6GAM71J7K3IMYN7M3JMN7IIR6F"  # For BNB, USDT-BEP20 - Get from https://bscscan.com/apis
POLYGONSCAN_API_KEY = "PGPXGH4Z6GAM71J7K3IMYN7M3JMN7IIR6F"  # For POL - Get from https://polygonscan.com/apis
SOLSCAN_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjcmVhdGVkQXQiOjE3NjMyOTM4MjE0NjcsImVtYWlsIjoiamFzaGFuc2luZ2hzYW5kaHUzMjVAZ21haWwuY29tIiwiYWN0aW9uIjoidG9rZW4tYXBpIiwiYXBpVmVyc2lvbiI6InYyIiwiaWF0IjoxNzYzMjkzODIxfQ.cNIj963wi7_6yU6C8LOEcnrPCh_2k3knewHgpBNx0gY"  # For SOL, USDT-SOL - Get from https://solscan.io/
TONSCAN_API_KEY = ""  # For TON, USDT-TON - Get from https://toncenter.com/api/v2/
TRONSCAN_API_KEY = "171d0578-bba9-4ff8-bd6e-ec71c33cdcda"  # For TRX, USDT-TRC20 - Get from https://www.trongrid.io/

# Web3 RPC URLs for EVM chains
BSC_RPC_URL = "https://bsc-dataseed1.binance.org"
ETH_RPC_URL = "https://eth.llamarpc.com"
POLYGON_RPC_URL = "https://polygon-rpc.com"

# Token contract addresses (USDT contracts on different chains)
USDT_BEP20_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"  # USDT on BSC
USDT_ERC20_CONTRACT = "0xdAC17F958D2ee523a2206206994597C13D831ec7"  # USDT on ETH
USDT_TRC20_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # USDT on Tron
USDT_SOL_CONTRACT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"  # USDT on Solana
USDT_TON_CONTRACT = "EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs"  # USDT on TON

# Deposit Configuration
MIN_DEPOSIT_USD = 10.0  # Minimum deposit in USD equivalent
DEPOSIT_TIMEOUT = 3600  # 1 hour in seconds
PRICE_UPDATE_INTERVAL = 30  # Price update every 30 seconds
BALANCE_UPDATE_INTERVAL = 300  # Balance revaluation every 5 minutes
DEPOSIT_SCAN_INTERVAL = 30  # Check blockchain every 30 seconds

# ==================== END CONFIGURATION SECTION ====================

# Import blockchain-specific libraries
try:
    from solana.keypair import Keypair as SolanaKeypair
    from solders.keypair import Keypair as SoldersKeypair
    import base58
    SOLANA_AVAILABLE = True
except ImportError:
    SOLANA_AVAILABLE = False
    logging.warning("Solana libraries not available. Install: pip install solana solders")

try:
    from tronpy import Tron
    from tronpy.keys import PrivateKey as TronPrivateKey
    TRON_AVAILABLE = True
except ImportError:
    TRON_AVAILABLE = False
    logging.warning("Tron library not available. Install: pip install tronpy")

try:
    from pytoniq_core import Address as TonAddress
    from pytoniq_core.crypto.keys import private_key_to_public_key
    TON_AVAILABLE = True
except ImportError:
    TON_AVAILABLE = False
    logging.warning("TON library not available. Install: pip install pytoniq-core")

# Initialize Web3 connections for EVM chains
try:
    w3_bsc = Web3(Web3.HTTPProvider(BSC_RPC_URL)) if BSC_RPC_URL else None
    w3_eth = Web3(Web3.HTTPProvider(ETH_RPC_URL)) if ETH_RPC_URL else None
    w3_polygon = Web3(Web3.HTTPProvider(POLYGON_RPC_URL)) if POLYGON_RPC_URL else None
except Exception as e:
    logging.error(f"Failed to initialize Web3 connections: {e}")
    w3_bsc = w3_eth = w3_polygon = None

# ERC20 ABI for token operations
ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], 
     "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], 
     "type": "function"},
    {"constant": False, "inputs": [{"name": "_to", "type": "address"}, 
     {"name": "_value", "type": "uint256"}], "name": "transfer", 
     "outputs": [{"name": "", "type": "bool"}], "type": "function"}
]

# Global state
CURRENT_ADDRESS_INDEX = 0
deposit_sessions = {}  # {user_id: session_data}
crypto_prices = {}  # {coin_id: price_usd}
crypto_user_deposits = {}  # {user_id: [{crypto, amount, timestamp}]}

# Supported cryptocurrencies metadata
DEPOSIT_METHODS = {
    "btc": {"name": "Bitcoin", "blockchain": "bitcoin", "type": "native", "decimals": 8,
            "explorer": "https://blockchain.info/tx/", "coin_id": "bitcoin", "active": True},
    "ltc": {"name": "Litecoin", "blockchain": "litecoin", "type": "native", "decimals": 8,
            "explorer": "https://live.blockcypher.com/ltc/tx/", "coin_id": "litecoin", "active": True},
    "eth": {"name": "Ethereum", "blockchain": "ethereum", "type": "native", "decimals": 18,
            "explorer": "https://etherscan.io/tx/", "coin_id": "ethereum", "active": True},
    "bnb": {"name": "BNB", "blockchain": "bsc", "type": "native", "decimals": 18,
            "explorer": "https://bscscan.com/tx/", "coin_id": "binancecoin", "active": True},
    "pol": {"name": "Polygon", "blockchain": "polygon", "type": "native", "decimals": 18,
            "explorer": "https://polygonscan.com/tx/", "coin_id": "matic-network", "active": True},
    "sol": {"name": "Solana", "blockchain": "solana", "type": "native", "decimals": 9,
            "explorer": "https://solscan.io/tx/", "coin_id": "solana", "active": SOLANA_AVAILABLE},
    "ton": {"name": "Toncoin", "blockchain": "ton", "type": "native", "decimals": 9,
            "explorer": "https://tonscan.org/tx/", "coin_id": "the-open-network", "active": TON_AVAILABLE},
    "doge": {"name": "Dogecoin", "blockchain": "dogecoin", "type": "native", "decimals": 8,
             "explorer": "https://dogechain.info/tx/", "coin_id": "dogecoin", "active": True},
    "trx": {"name": "Tron", "blockchain": "tron", "type": "native", "decimals": 6,
            "explorer": "https://tronscan.org/#/transaction/", "coin_id": "tron", "active": TRON_AVAILABLE},
    "usdt_bep20": {"name": "USDT (BEP20)", "blockchain": "bsc", "type": "token", "contract": USDT_BEP20_CONTRACT,
                   "decimals": 18, "explorer": "https://bscscan.com/tx/", "coin_id": "tether", "active": True},
    "usdt_erc20": {"name": "USDT (ERC20)", "blockchain": "ethereum", "type": "token", "contract": USDT_ERC20_CONTRACT,
                   "decimals": 6, "explorer": "https://etherscan.io/tx/", "coin_id": "tether", "active": True},
    "usdt_trc20": {"name": "USDT (TRC20)", "blockchain": "tron", "type": "token", "contract": USDT_TRC20_CONTRACT,
                   "decimals": 6, "explorer": "https://tronscan.org/#/transaction/", "coin_id": "tether", "active": TRON_AVAILABLE},
    "usdt_sol": {"name": "USDT (SOL)", "blockchain": "solana", "type": "token", "contract": USDT_SOL_CONTRACT,
                 "decimals": 6, "explorer": "https://solscan.io/tx/", "coin_id": "tether", "active": SOLANA_AVAILABLE},
    "usdt_ton": {"name": "USDT (TON)", "blockchain": "ton", "type": "token", "contract": USDT_TON_CONTRACT,
                 "decimals": 6, "explorer": "https://tonscan.org/tx/", "coin_id": "tether", "active": TON_AVAILABLE}
}


def init_deposit_system(
    master_keys_dict=None,
    central_wallets_dict=None,
    api_keys_dict=None,
    bot_owner_id=None
):
    """
    Initialize the deposit system with configuration from casino.py
    This allows the main bot to pass its configuration to this module
    """
    global MASTER_PRIVATE_KEY_BTC, MASTER_PRIVATE_KEY_LTC, MASTER_PRIVATE_KEY_ETH
    global MASTER_PRIVATE_KEY_BNB, MASTER_PRIVATE_KEY_SOL, MASTER_PRIVATE_KEY_TON
    global MASTER_PRIVATE_KEY_DOGE, MASTER_PRIVATE_KEY_TRX
    global CENTRAL_WALLET_ADDRESS_BTC, CENTRAL_WALLET_ADDRESS_LTC, CENTRAL_WALLET_ADDRESS_ETH
    global CENTRAL_WALLET_ADDRESS_BNB, CENTRAL_WALLET_ADDRESS_SOL, CENTRAL_WALLET_ADDRESS_TON
    global CENTRAL_WALLET_ADDRESS_DOGE, CENTRAL_WALLET_ADDRESS_TRX
    global BLOCKCYPHER_API_KEY, ETHERSCAN_API_KEY, BSCSCAN_API_KEY
    global POLYGONSCAN_API_KEY, SOLSCAN_API_KEY, TONSCAN_API_KEY, TRONSCAN_API_KEY
    global BOT_OWNER_ID
    
    if master_keys_dict:
        MASTER_PRIVATE_KEY_BTC = master_keys_dict.get('btc', '')
        MASTER_PRIVATE_KEY_LTC = master_keys_dict.get('ltc', '')
        MASTER_PRIVATE_KEY_ETH = master_keys_dict.get('eth', '')
        MASTER_PRIVATE_KEY_BNB = master_keys_dict.get('bnb', '')
        MASTER_PRIVATE_KEY_SOL = master_keys_dict.get('sol', '')
        MASTER_PRIVATE_KEY_TON = master_keys_dict.get('ton', '')
        MASTER_PRIVATE_KEY_DOGE = master_keys_dict.get('doge', '')
        MASTER_PRIVATE_KEY_TRX = master_keys_dict.get('trx', '')
    
    if central_wallets_dict:
        CENTRAL_WALLET_ADDRESS_BTC = central_wallets_dict.get('btc', '')
        CENTRAL_WALLET_ADDRESS_LTC = central_wallets_dict.get('ltc', '')
        CENTRAL_WALLET_ADDRESS_ETH = central_wallets_dict.get('eth', '')
        CENTRAL_WALLET_ADDRESS_BNB = central_wallets_dict.get('bnb', '')
        CENTRAL_WALLET_ADDRESS_SOL = central_wallets_dict.get('sol', '')
        CENTRAL_WALLET_ADDRESS_TON = central_wallets_dict.get('ton', '')
        CENTRAL_WALLET_ADDRESS_DOGE = central_wallets_dict.get('doge', '')
        CENTRAL_WALLET_ADDRESS_TRX = central_wallets_dict.get('trx', '')
    
    if api_keys_dict:
        BLOCKCYPHER_API_KEY = api_keys_dict.get('blockcypher', '')
        ETHERSCAN_API_KEY = api_keys_dict.get('etherscan', '')
        BSCSCAN_API_KEY = api_keys_dict.get('bscscan', '')
        POLYGONSCAN_API_KEY = api_keys_dict.get('polygonscan', '')
        SOLSCAN_API_KEY = api_keys_dict.get('solscan', '')
        TONSCAN_API_KEY = api_keys_dict.get('tonscan', '')
        TRONSCAN_API_KEY = api_keys_dict.get('tronscan', '')
    
    if bot_owner_id:
        BOT_OWNER_ID = bot_owner_id
    
    logging.info("Deposit system initialized with external configuration")


# For backwards compatibility, expose the same interface as the old system
async def show_deposit_menu(update, context, user, from_callback=True):
    """Show deposit menu with all supported cryptocurrencies"""
    query = update.callback_query if from_callback else None
    
    keyboard = []
    
    # Group by native vs token
    native_coins = [(k, v) for k, v in DEPOSIT_METHODS.items() if v["type"] == "native" and v.get("active")]
    token_coins = [(k, v) for k, v in DEPOSIT_METHODS.items() if v["type"] == "token" and v.get("active")]
    
    # Add native coins (2 per row)
    for i in range(0, len(native_coins), 2):
        row = []
        for j in range(2):
            if i + j < len(native_coins):
                key, method = native_coins[i + j]
                row.append(InlineKeyboardButton(
                    method["name"],
                    callback_data=f"deposit_{key}"
                ))
        keyboard.append(row)
    
    # Add USDT options if available
    if token_coins:
        keyboard.append([InlineKeyboardButton("💵 USDT (Multiple Chains)", callback_data="deposit_usdt_menu")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")])
    
    text = (
        f"💰 <b>Select Deposit Method:</b>\n\n"
        f"⚠️ You will receive a temporary address (valid for 1 hour)\n"
        f"💵 Minimum deposit: <b>${MIN_DEPOSIT_USD}</b> equivalent\n\n"
        f"🔹 Choose your preferred cryptocurrency:"
    )
    
    if from_callback and query:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_usdt_menu(update, context):
    """Show USDT chain selection"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("USDT (BEP20) - BSC", callback_data="deposit_usdt_bep20")],
        [InlineKeyboardButton("USDT (ERC20) - ETH", callback_data="deposit_usdt_erc20")],
        [InlineKeyboardButton("USDT (TRC20) - Tron", callback_data="deposit_usdt_trc20")],
        [InlineKeyboardButton("USDT (SOL) - Solana", callback_data="deposit_usdt_sol")],
        [InlineKeyboardButton("USDT (TON) - TON Network", callback_data="deposit_usdt_ton")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_deposit")]
    ]
    
    text = (
        "💵 <b>Select USDT Chain:</b>\n\n"
        "Choose the blockchain network:\n\n"
        "• <b>BEP20</b> - Binance Smart Chain (Low fees)\n"
        "• <b>ERC20</b> - Ethereum (Higher fees)\n"
        "• <b>TRC20</b> - Tron (Very low fees)\n"
        "• <b>SOL</b> - Solana (Fast & cheap)\n"
        "• <b>TON</b> - TON Network"
    )
    
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))


# Expose main functions
__all__ = [
    'init_deposit_system',
    'show_deposit_menu',
    'show_usdt_menu',
    'DEPOSIT_METHODS',
    'MIN_DEPOSIT_USD',
    'deposit_sessions',
    'crypto_prices',
    'crypto_user_deposits',
]

logging.info("Deposit module loaded successfully")
