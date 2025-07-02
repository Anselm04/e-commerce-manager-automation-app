# AI E-Commerce Manager

An advanced AI-powered application that provides automated management for online businesses. This comprehensive tool streamlines operations through intelligent automation of various e-commerce processes, enabling business owners to focus on growth and strategy rather than day-to-day management tasks.

## Features

### Core Capabilities
- **Inventory Management**: Automated tracking, alerts for low stock, and inventory optimization
- **Sales Analytics**: Comprehensive data analysis, trend identification, and sales forecasting
- **Customer Relationship Management**: Customer segmentation, behavior analysis, and personalized engagement
- **Marketing Automation**: Automated campaign creation, scheduling, and performance tracking
- **Order Processing**: Streamlined order fulfillment, tracking, and management
- **Reporting Tools**: Customizable dashboards and exportable reports for business insights

### Advanced Features
- **E-commerce and Affiliate Marketing Support**: Tools for managing affiliate programs and multiple sales channels
- **Shopify Store Management and Automation**: Deep integration with Shopify for enhanced store management
- **Dynamic Pricing Adjustments**: AI-driven price optimization based on market conditions and demand
- **Trending Product Identification**: Automated discovery of trending products for inventory decisions
- **API Key Collection for Integrations**: Centralized management of API integrations with third-party services

## Installation

Install the required dependencies:

```bash
pip install fastapi uvicorn requests shopify pandas openai sqlalchemy psycopg2-binary
```

## Usage

1. Configure your API keys and service integrations in the configuration file
2. Run the application:
   ```bash
   python app.py
   ```
3. Access the dashboard through the web interface or API endpoints

## Integrations

The application supports integration with various third-party services:
- Payment gateways (Stripe, PayPal, etc.)
- Shipping providers (FedEx, UPS, etc.)
- Analytics platforms (Google Analytics, Mixpanel, etc.)
- Email marketing services (Mailchimp, SendGrid, etc.)
- E-commerce platforms (Shopify, WooCommerce, etc.)

## Configuration

Configuration is managed through a JSON file that specifies:
- API credentials for third-party services
- Business rules and preferences
- Automation settings and thresholds
- Reporting preferences

For detailed documentation on configuration options, refer to the configuration guide.jarvis-cj-auto-split/
├── README.md
├── .env.example
├── package.json
├── server.js
├── /lib/
│   ├── cjPricing.js
│   ├── payCJ.js
│   └── payoutProfit.js
├── /webhook/
│   └── shopifyWebhook.js
├── Dockerfile (optional for local testing)
└── deploy.sh (optional for serverless deployment)
# Jarvis Auto-Split CJ System 🤖

An automated payment engine for Shopify + CJdropshipping that:
- Automatically retrieves real-time CJ pricing
- Pays CJ via PayPal
- Routes profit to your Stripe/NZ bank account
- Logs everything for accounting
- Requires zero manual action once deployed

---

## 🚀 1. Setup Instructions

### Prerequisites

- Shopify Store
- PayPal Business Account
- Stripe Account
- CJdropshipping API Access

---

### 🔐 2. Clone the Repo

```bash
git clone https://github.com/YOUR_USERNAME/jarvis-cj-auto-split.git
cd jarvis-cj-auto-split
SHOPIFY_WEBHOOK_SECRET=your_webhook_secret
CJ_API_KEY=your_cj_key
CJ_API_SECRET=your_cj_secret
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_SECRET=your_paypal_secret
PAYPAL_CJ_ACCOUNT_EMAIL=cj@example.com
STRIPE_SECRET_KEY=your_stripe_secret_key
npm install
node server.js
---

### 📦 `package.json`

```json
{
  "name": "jarvis-cj-auto-split",
  "version": "1.0.0",
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "@paypal/payouts-sdk": "^1.0.0",
    "axios": "^1.6.0",
    "crypto": "^1.0.1",
    "express": "^4.18.2",
    "stripe": "^12.5.0"
  }
}SHOPIFY_WEBHOOK_SECRET=shpss_***
CJ_API_KEY=cj_key_here
CJ_API_SECRET=cj_secret_here
PAYPAL_CLIENT_ID=***
PAYPAL_SECRET=***
PAYPAL_CJ_ACCOUNT_EMAIL=cj@paypal.com
STRIPE_SECRET_KEY=sk_live_***
const express = require('express');
const axios = require('axios');
const crypto = require('crypto');
const app = express();

app.use(express.json());

// Environment variables expected:
// SHOPIFY_WEBHOOK_SECRET
// CJ_API_KEY, CJ_API_SECRET
// PAYPAL_CLIENT_ID, PAYPAL_SECRET, PAYPAL_CJ_ACCOUNT_EMAIL
// STRIPE_SECRET_KEY
// PROFIT_ACCOUNT_PAYOUT_ID (Stripe Connected Account or your Stripe account)

function verifyShopifyWebhook(req, res, buf) {
  const hmac = req.headers['x-shopify-hmac-sha256'];
  const body = buf.toString('utf8');
  const hash = crypto
    .createHmac('sha256', process.env.SHOPIFY_WEBHOOK_SECRET)
    .update(body, 'utf8')
    .digest('base64');

  if (hash !== hmac) {
    throw new Error('Invalid Shopify webhook signature');
  }
}

app.post('/shopify/order-created', express.raw({ type: 'application/json' }), (req, res) => {
  try {
    verifyShopifyWebhook(req, res, req.body);
  } catch (err) {
    return res.status(401).send('Unauthorized');
  }

  const order = JSON.parse(req.body.toString());

  // Process order asynchronously
  processOrder(order).then(() => {
    res.status(200).send('Order processed');
  }).catch(err => {
    console.error('Order processing failed:', err);
    res.status(500).send('Processing error');
  });
});

async function processOrder(order) {
  // Extract SKUs and quantities from Shopify order items
  const items = order.line_items.map(item => ({
    sku: item.sku || item.variant_sku || item.variant_id.toString(),
    quantity: item.quantity
  }));

  // Step 1: Get live price from CJdropshipping
  const cjPricing = await getCJPrice(items);

  // Step 2: Calculate payment amounts
  const totalCJCost = cjPricing.totalCost; // includes product + shipping + taxes

  // Step 3: Pay CJ via PayPal automatically
  await payCJviaPayPal(totalCJCost);

  // Step 4: Calculate profit (order.total_price - totalCJCost)
  const profit = parseFloat(order.total_price) - totalCJCost;

  // Step 5: Route profit to your Stripe account payout
  await payoutProfitStripe(profit);

  // Step 6: Log transaction (can be implemented with DB or file)
  console.log(`Order ${order.id}: CJ paid $${totalCJCost}, profit $${profit}`);
}

// CJdropshipping API example (mocked)
async function getCJPrice(items) {
  // Compose request for CJ pricing API
  // API docs: https://cjdropshipping.com/API
  const apiUrl = 'https://api.cjdropshipping.com/api/order/price';

  const body = {
    skuList: items.map(i => ({ sku: i.sku, quantity: i.quantity }))
  };

  const response = await axios.post(apiUrl, body, {
    headers: {
      'Content-Type': 'application/json',
      'CJ-API-KEY': process.env.CJ_API_KEY,
      'CJ-API-SECRET': process.env.CJ_API_SECRET,
    }
  });

  if (response.data.code !== 200) {
    throw new Error(`CJ API error: ${response.data.msg}`);
  }

  return {
    totalCost: parseFloat(response.data.data.totalPrice)
  };
}

// Pay CJ automatically via PayPal (PayPal Payouts API)
const paypal = require('@paypal/payouts-sdk');

const payPalClient = new paypal.core.PayPalHttpClient(new paypal.core.SandboxEnvironment(
  process.env.PAYPAL_CLIENT_ID,
  process.env.PAYPAL_SECRET
));

async function payCJviaPayPal(amount) {
  const request = new paypal.payouts.PayoutsPostRequest();
  request.requestBody({
    sender_batch_header: {
      sender_batch_id: `batch_${Date.now()}`,
      email_subject: "CJ Payment Payout"
    },
    items: [{
      recipient_type: "EMAIL",
      amount: {
        value: amount.toFixed(2),
        currency: "USD"
      },
      receiver: process.env.PAYPAL_CJ_ACCOUNT_EMAIL,
      note: "Automated payment to CJdropshipping",
      sender_item_id: `cj_pay_${Date.now()}`
    }]
  });

  const response = await payPalClient.execute(request);
  if (response.statusCode !== 201) {
    throw new Error('PayPal payout failed');
  }
}

// Stripe profit payout (assuming standard Stripe account)
const Stripe = require('stripe');
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

async function payoutProfitStripe(amount) {
  // Amount in cents
  const payoutAmount = Math.round(amount * 100);
  if (payoutAmount <= 0) {
    console.log('Profit zero or negative, skipping payout');
    return;
  }

  // Create a transfer to connected account or your Stripe balance transfer
  // Here we assume payout to your default bank account (automatic payouts enabled)

  // Normally, Stripe automatically pays out your balance on schedule.
  // If immediate payout needed, use Stripe Instant Payouts (requires eligibility)
  // Here, we assume profit is already in Stripe balance from customer payment,
  // so no transfer needed, just logging.

  console.log(`Profit $${amount.toFixed(2)} ready for payout via Stripe.`);
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Jarvis Auto-Split CJ server running on port ${PORT}`);
});
SHOPIFY_WEBHOOK_SECRET=your_shopify_webhook_secret
CJ_API_KEY=your_cj_api_key
CJ_API_SECRET=your_cj_api_secret
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_SECRET=your_paypal_secret
PAYPAL_CJ_ACCOUNT_EMAIL=cj@paypalemail.com
STRIPE_SECRET_KEY=your_stripe_secret_key
PORT=3000
async function processOrder(order) {
  const items = order.line_items.map(item => ({
    sku: item.sku || item.variant_sku || item.variant_id.toString(),
    quantity: item.quantity
  }));

  // STEP 1: Get real-time CJ price
  const cjPricing = await getCJPrice(items);
  const totalCJCost = cjPricing.totalCost;

  // STEP 2: Determine payment method (universal capture)
  const paymentMethod = order.gateway.toLowerCase(); // e.g. paypal, stripe, shopify_payments, laybuy, klarna, crypto

  console.log(`Payment method used: ${paymentMethod}`);

  // STEP 3: Automatically pay CJ via PayPal
  await payCJviaPayPal(totalCJCost);

  // STEP 4: Calculate profit
  const totalPaidByCustomer = parseFloat(order.total_price);
  const profit = totalPaidByCustomer - totalCJCost;

  // STEP 5: Route profit based on payment method
  if (paymentMethod.includes("paypal")) {
    // Funds go to your PayPal → you can manually or automatically transfer to bank
    console.log("Profit held in PayPal — consider PayPal Payout to bank.");
  } else {
    // Most other methods → Shopify sends to Stripe → Stripe handles bank payout
    await payoutProfitStripe(profit);
  }

  // STEP 6: Log result
  console.log(`Order ${order.id} handled. CJ paid: $${totalCJCost}, profit: $${profit}, method: ${paymentMethod}`);
}
// Shopify sends the payment method in 'gateway' field
// Examples:
// - PayPal: "paypal"
// - Stripe: "stripe"
// - Shopify: "shopify_payments"
// - Buy Now Pay Later: "afterpay", "klarna", etc.
// - Crypto: "coinbase", "bitpay", etc.
module.exports = function detectSupplier(item) {
  // You can expand this logic to use product tags, vendors, or SKU prefixes
  const sku = item.sku.toLowerCase();

  if (sku.startsWith("cj-") || item.vendor === "CJdropshipping") {
    return "cj";
  }

  if (sku.startsWith("zd-") || item.vendor === "Zendrop") {
    return "zendrop";
  }

  if (sku.startsWith("sp-") || item.vendor === "Spocket") {
    return "spocket";
  }

  if (sku.startsWith("al-") || item.vendor === "Alibaba") {
    return "alibaba";
  }

  return "unknown"; // fallback or error
};
const detectSupplier = require('./lib/supplierRouter');

async function processOrder(order) {
  const groupedItems = {};

  for (const item of order.line_items) {
    const supplier = detectSupplier(item);

    if (!groupedItems[supplier]) groupedItems[supplier] = [];
    groupedItems[supplier].push({
      sku: item.sku || item.variant_sku || item.variant_id.toString(),
      quantity: item.quantity
    });
  }

  let totalCJCost = 0;
  let totalSupplierCost = 0;

  // Handle each supplier individually
  for (const [supplier, items] of Object.entries(groupedItems)) {
    switch (supplier) {
      case 'cj':
        const cjPricing = await getCJPrice(items);
        totalCJCost += cjPricing.totalCost;
        await payCJviaPayPal(cjPricing.totalCost);
        break;

      case 'zendrop':
        // Placeholder for future Zendrop integration
        console.log(`[Jarvis] Zendrop supplier logic coming soon...`);
        break;

      case 'spocket':
        console.log(`[Jarvis] Spocket support not yet active`);
        break;

      case 'alibaba':
        console.log(`[Jarvis] Alibaba supplier logic reserved for enterprise orders`);
        break;

      default:
        console.warn(`Unknown supplier for item(s):`, items);
    }
  }

  const profit = parseFloat(order.total_price) - totalCJCost;
  await payoutProfitStripe(profit);

  console.log(`Order ${order.id}: Total supplier cost $${totalCJCost}, profit $${profit}`);
}
git clone https://github.com/YOUR_USERNAME/jarvis-cj-auto-split.git
cd jarvis-cj-auto-split
SHOPIFY_WEBHOOK_SECRET=your_webhook_secret
CJ_API_KEY=your_cj_key
CJ_API_SECRET=your_cj_secret
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_SECRET=your_paypal_secret
PAYPAL_CJ_ACCOUNT_EMAIL=cj@example.com
STRIPE_SECRET_KEY=your_stripe_secret_key
npm install
node server.js
---

### 📦 `package.json`

```json
{
  "name": "jarvis-cj-auto-split",
  "version": "1.0.0",
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "@paypal/payouts-sdk": "^1.0.0",
    "axios": "^1.6.0",
    "crypto": "^1.0.1",
    "express": "^4.18.2",
    "stripe": "^12.5.0"
  }
}SHOPIFY_WEBHOOK_SECRET=shpss_***
CJ_API_KEY=cj_key_here
CJ_API_SECRET=cj_secret_here
PAYPAL_CLIENT_ID=***
PAYPAL_SECRET=***
PAYPAL_CJ_ACCOUNT_EMAIL=cj@paypal.com
STRIPE_SECRET_KEY=sk_live_***
const express = require('express');
const axios = require('axios');
const crypto = require('crypto');
const app = express();

app.use(express.json());

// Environment variables expected:
// SHOPIFY_WEBHOOK_SECRET
// CJ_API_KEY, CJ_API_SECRET
// PAYPAL_CLIENT_ID, PAYPAL_SECRET, PAYPAL_CJ_ACCOUNT_EMAIL
// STRIPE_SECRET_KEY
// PROFIT_ACCOUNT_PAYOUT_ID (Stripe Connected Account or your Stripe account)

function verifyShopifyWebhook(req, res, buf) {
  const hmac = req.headers['x-shopify-hmac-sha256'];
  const body = buf.toString('utf8');
  const hash = crypto
    .createHmac('sha256', process.env.SHOPIFY_WEBHOOK_SECRET)
    .update(body, 'utf8')
    .digest('base64');

  if (hash !== hmac) {
    throw new Error('Invalid Shopify webhook signature');
  }
}

app.post('/shopify/order-created', express.raw({ type: 'application/json' }), (req, res) => {
  try {
    verifyShopifyWebhook(req, res, req.body);
  } catch (err) {
    return res.status(401).send('Unauthorized');
  }

  const order = JSON.parse(req.body.toString());

  // Process order asynchronously
  processOrder(order).then(() => {
    res.status(200).send('Order processed');
  }).catch(err => {
    console.error('Order processing failed:', err);
    res.status(500).send('Processing error');
  });
});

async function processOrder(order) {
  // Extract SKUs and quantities from Shopify order items
  const items = order.line_items.map(item => ({
    sku: item.sku || item.variant_sku || item.variant_id.toString(),
    quantity: item.quantity
  }));

  // Step 1: Get live price from CJdropshipping
  const cjPricing = await getCJPrice(items);

  // Step 2: Calculate payment amounts
  const totalCJCost = cjPricing.totalCost; // includes product + shipping + taxes

  // Step 3: Pay CJ via PayPal automatically
  await payCJviaPayPal(totalCJCost);

  // Step 4: Calculate profit (order.total_price - totalCJCost)
  const profit = parseFloat(order.total_price) - totalCJCost;

  // Step 5: Route profit to your Stripe account payout
  await payoutProfitStripe(profit);

  // Step 6: Log transaction (can be implemented with DB or file)
  console.log(`Order ${order.id}: CJ paid $${totalCJCost}, profit $${profit}`);
}

// CJdropshipping API example (mocked)
async function getCJPrice(items) {
  // Compose request for CJ pricing API
  // API docs: https://cjdropshipping.com/API
  const apiUrl = 'https://api.cjdropshipping.com/api/order/price';

  const body = {
    skuList: items.map(i => ({ sku: i.sku, quantity: i.quantity }))
  };

  const response = await axios.post(apiUrl, body, {
    headers: {
      'Content-Type': 'application/json',
      'CJ-API-KEY': process.env.CJ_API_KEY,
      'CJ-API-SECRET': process.env.CJ_API_SECRET,
    }
  });

  if (response.data.code !== 200) {
    throw new Error(`CJ API error: ${response.data.msg}`);
  }

  return {
    totalCost: parseFloat(response.data.data.totalPrice)
  };
}

// Pay CJ automatically via PayPal (PayPal Payouts API)
const paypal = require('@paypal/payouts-sdk');

const payPalClient = new paypal.core.PayPalHttpClient(new paypal.core.SandboxEnvironment(
  process.env.PAYPAL_CLIENT_ID,
  process.env.PAYPAL_SECRET
));

async function payCJviaPayPal(amount) {
  const request = new paypal.payouts.PayoutsPostRequest();
  request.requestBody({
    sender_batch_header: {
      sender_batch_id: `batch_${Date.now()}`,
      email_subject: "CJ Payment Payout"
    },
    items: [{
      recipient_type: "EMAIL",
      amount: {
        value: amount.toFixed(2),
        currency: "USD"
      },
      receiver: process.env.PAYPAL_CJ_ACCOUNT_EMAIL,
      note: "Automated payment to CJdropshipping",
      sender_item_id: `cj_pay_${Date.now()}`
    }]
  });

  const response = await payPalClient.execute(request);
  if (response.statusCode !== 201) {
    throw new Error('PayPal payout failed');
  }
}

// Stripe profit payout (assuming standard Stripe account)
const Stripe = require('stripe');
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

async function payoutProfitStripe(amount) {
  // Amount in cents
  const payoutAmount = Math.round(amount * 100);
  if (payoutAmount <= 0) {
    console.log('Profit zero or negative, skipping payout');
    return;
  }

  // Create a transfer to connected account or your Stripe balance transfer
  // Here we assume payout to your default bank account (automatic payouts enabled)

  // Normally, Stripe automatically pays out your balance on schedule.
  // If immediate payout needed, use Stripe Instant Payouts (requires eligibility)
  // Here, we assume profit is already in Stripe balance from customer payment,
  // so no transfer needed, just logging.

  console.log(`Profit $${amount.toFixed(2)} ready for payout via Stripe.`);
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Jarvis Auto-Split CJ server running on port ${PORT}`);
});
SHOPIFY_WEBHOOK_SECRET=your_shopify_webhook_secret
CJ_API_KEY=your_cj_api_key
CJ_API_SECRET=your_cj_api_secret
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_SECRET=your_paypal_secret
PAYPAL_CJ_ACCOUNT_EMAIL=cj@paypalemail.com
STRIPE_SECRET_KEY=your_stripe_secret_key
PORT=3000
async function processOrder(order) {
  const items = order.line_items.map(item => ({
    sku: item.sku || item.variant_sku || item.variant_id.toString(),
    quantity: item.quantity
  }));

  // STEP 1: Get real-time CJ price
  const cjPricing = await getCJPrice(items);
  const totalCJCost = cjPricing.totalCost;

  // STEP 2: Determine payment method (universal capture)
  const paymentMethod = order.gateway.toLowerCase(); // e.g. paypal, stripe, shopify_payments, laybuy, klarna, crypto

  console.log(`Payment method used: ${paymentMethod}`);

  // STEP 3: Automatically pay CJ via PayPal
  await payCJviaPayPal(totalCJCost);

  // STEP 4: Calculate profit
  const totalPaidByCustomer = parseFloat(order.total_price);
  const profit = totalPaidByCustomer - totalCJCost;

  // STEP 5: Route profit based on payment method
  if (paymentMethod.includes("paypal")) {
    // Funds go to your PayPal → you can manually or automatically transfer to bank
    console.log("Profit held in PayPal — consider PayPal Payout to bank.");
  } else {
    // Most other methods → Shopify sends to Stripe → Stripe handles bank payout
    await payoutProfitStripe(profit);
  }

  // STEP 6: Log result
  console.log(`Order ${order.id} handled. CJ paid: $${totalCJCost}, profit: $${profit}, method: ${paymentMethod}`);
}
// Shopify sends the payment method in 'gateway' field
// Examples:
// - PayPal: "paypal"
// - Stripe: "stripe"
// - Shopify: "shopify_payments"
// - Buy Now Pay Later: "afterpay", "klarna", etc.
// - Crypto: "coinbase", "bitpay", etc.
module.exports = function detectSupplier(item) {
  // You can expand this logic to use product tags, vendors, or SKU prefixes
  const sku = item.sku.toLowerCase();

  if (sku.startsWith("cj-") || item.vendor === "CJdropshipping") {
    return "cj";
  }

  if (sku.startsWith("zd-") || item.vendor === "Zendrop") {
    return "zendrop";
  }

  if (sku.startsWith("sp-") || item.vendor === "Spocket") {
    return "spocket";
  }

  if (sku.startsWith("al-") || item.vendor === "Alibaba") {
    return "alibaba";
  }

  return "unknown"; // fallback or error
};
const detectSupplier = require('./lib/supplierRouter');

async function processOrder(order) {
  const groupedItems = {};

  for (const item of order.line_items) {
    const supplier = detectSupplier(item);

    if (!groupedItems[supplier]) groupedItems[supplier] = [];
    groupedItems[supplier].push({
      sku: item.sku || item.variant_sku || item.variant_id.toString(),
      quantity: item.quantity
    });
  }

  let totalCJCost = 0;
  let totalSupplierCost = 0;

  // Handle each supplier individually
  for (const [supplier, items] of Object.entries(groupedItems)) {
    switch (supplier) {
      case 'cj':
        const cjPricing = await getCJPrice(items);
        totalCJCost += cjPricing.totalCost;
        await payCJviaPayPal(cjPricing.totalCost);
        break;

      case 'zendrop':
        // Placeholder for future Zendrop integration
        console.log(`[Jarvis] Zendrop supplier logic coming soon...`);
        break;

      case 'spocket':
        console.log(`[Jarvis] Spocket support not yet active`);
        break;

      case 'alibaba':
        console.log(`[Jarvis] Alibaba supplier logic reserved for enterprise orders`);
        break;

      default:
        console.warn(`Unknown supplier for item(s):`, items);
    }
  }

  const profit = parseFloat(order.total_price) - totalCJCost;
  await payoutProfitStripe(profit);

  console.log(`Order ${order.id}: Total supplier cost $${totalCJCost}, profit $${profit}`);
}
const axios = require('axios');
const shopify = require('./lib/shopifyAPI'); // wrapper for Shopify API
const categorizeProduct = require('./lib/categorizer'); // AI-based categorizer
const suppliers = require('./lib/suppliers'); // modular importers

async function importAllSupplierCatalogs() {
  for (const supplier of suppliers.list) {
    console.log(`[Jarvis] Pulling catalog from ${supplier.name}...`);
    const products = await supplier.fetchCatalog();

    for (const product of products) {
      // Step 1: Categorize
      const { category, subcategory, tags } = categorizeProduct(product);

      // Step 2: Prepare Shopify product payload
      const shopifyProduct = {
        title: product.name,
        body_html: product.description,
        vendor: supplier.name,
        product_type: category,
        tags: [...tags, subcategory],
        variants: [
          {
            price: (product.cost * 1.5).toFixed(2),
            sku: product.sku,
            inventory_quantity: product.stock,
            inventory_management: "shopify"
          }
        ],
        images: product.images.map(img => ({ src: img }))
      };

      // Step 3: Upload to Shopify
      try {
        await shopify.createProduct(shopifyProduct);
        console.log(`[Jarvis] Uploaded ${product.name}`);
      } catch (err) {
        console.error(`[ERROR] Failed to upload product ${product.name}:`, err.message);
      }
    }
  }
}
module.exports = function categorizeProduct(product) {
  const title = product.name.toLowerCase();

  if (title.includes("hoodie") || title.includes("sweater")) {
    return { category: "Apparel", subcategory: "Hoodies", tags: ["fashion", "winter"] };
  }
  if (title.includes("mug") || title.includes("cup")) {
    return { category: "Home & Kitchen", subcategory: "Drinkware", tags: ["kitchen", "coffee"] };
  }

  return { category: "Miscellaneous", subcategory: "Other", tags: ["general"] };
};
const cj = require('./suppliers/cj');
const zendrop = require('./suppliers/zendrop');
const spocket = require('./suppliers/spocket');

module.exports.list = [cj, zendrop, spocket];
const axios = require('axios');

module.exports.name = "CJdropshipping";

module.exports.fetchCatalog = async function () {
  const response = await axios.get("https://api.cjdropshipping.com/products", {
    headers: {
      "Authorization": `Bearer ${process.env.CJ_API_KEY}`
    }
  });
  return response.data.products.map(p => ({
    name: p.title,
    description: p.description,
    sku: p.sku,
    cost: p.cost,
    stock: p.stock,
    images: p.images
  }));
};
const axios = require('axios');

module.exports.createProduct = async function (product) {
  const response = await axios.post(
    `https://${process.env.SHOPIFY_STORE}/admin/api/2023-01/products.json`,
    { product },
    {
      headers: {
        "X-Shopify-Access-Token": process.env.SHOPIFY_ADMIN_TOKEN
      }
    }
  );
  return response.data.product;
};
/**
 * Jarvis Universal Product Importer – Single File Version
 * Automatically pulls catalogs, categorizes, and uploads to Shopify
 */

const axios = require('axios');
require('dotenv').config();

// === Categorization Logic ===
function categorizeProduct(product) {
  const title = product.name.toLowerCase();

  if (title.includes("hoodie")) return { category: "Apparel", subcategory: "Hoodies", tags: ["fashion"] };
  if (title.includes("shirt")) return { category: "Apparel", subcategory: "Shirts", tags: ["clothing", "casual"] };
  if (title.includes("mug")) return { category: "Home & Kitchen", subcategory: "Drinkware", tags: ["kitchen", "coffee"] };
  if (title.includes("jewelry") || title.includes("necklace")) return { category: "Accessories", subcategory: "Jewelry", tags: ["style"] };

  return { category: "Miscellaneous", subcategory: "Other", tags: ["general"] };
}

// === Shopify Upload Function ===
async function createShopifyProduct(product) {
  const res = await axios.post(
    `https://${process.env.SHOPIFY_STORE}/admin/api/2023-01/products.json`,
    { product },
    {
      headers: {
        "X-Shopify-Access-Token": process.env.SHOPIFY_ADMIN_TOKEN,
        "Content-Type": "application/json"
      }
    }
  );
  return res.data.product;
}

// === CJdropshipping Catalog Fetch ===
async function fetchCJCatalog() {
  const res = await axios.get("https://api.cjdropshipping.com/products", {
    headers: {
      "Authorization": `Bearer ${process.env.CJ_API_KEY}`
    }
  });

  return res.data.products.map(p => ({
    name: p.title,
    description: p.description,
    sku: p.sku,
    cost: p.cost,
    stock: p.stock,
    images: p.images
  }));
}

// === Master Import Function ===
async function importAllProducts() {
  console.log("[Jarvis] Starting Universal Import...");
  const products = await fetchCJCatalog();

  for (const product of products) {
    const { category, subcategory, tags } = categorizeProduct(product);

    const shopifyProduct = {
      title: product.name,
      body_html: product.description,
      vendor: "CJdropshipping",
      product_type: category,
      tags: [...tags, subcategory],
      variants: [
        {
          price: (product.cost * 1.5).toFixed(2),
          sku: product.sku,
          inventory_quantity: product.stock,
          inventory_management: "shopify"
        }
      ],
      images: product.images.map(img => ({ src: img }))
    };

    try {
      await createShopifyProduct(shopifyProduct);
      console.log(`[✅ Uploaded] ${product.name}`);
    } catch (err) {
      console.error(`[❌ Error] ${product.name} — ${err.message}`);
    }
  }

  console.log("[Jarvis] Import Complete.");
}

// === Execute ===
importAllProducts();
SHOPIFY_STORE=your-store-name.myshopify.com
SHOPIFY_ADMIN_TOKEN=your_shopify_admin_token
CJ_API_KEY=your_cj_api_key
npm install axios dotenv
node jarvis-importer.js
/**
 * Jarvis Universal Multi-Supplier Importer – Future-Ready Global Dropshipping Engine
 * Supports CJdropshipping and extensible to any dropshipping supplier worldwide
 */

const axios = require('axios');
require('dotenv').config();

// === Categorization Engine ===
function categorizeProduct(product) {
  const title = product.name.toLowerCase();

  if (title.includes("hoodie")) return { category: "Apparel", subcategory: "Hoodies", tags: ["fashion"] };
  if (title.includes("shirt")) return { category: "Apparel", subcategory: "Shirts", tags: ["clothing", "casual"] };
  if (title.includes("mug")) return { category: "Home & Kitchen", subcategory: "Drinkware", tags: ["kitchen", "coffee"] };
  if (title.includes("jewelry") || title.includes("necklace")) return { category: "Accessories", subcategory: "Jewelry", tags: ["style"] };

  return { category: "Miscellaneous", subcategory: "Other", tags: ["general"] };
}

// === Shopify Upload ===
async function createShopifyProduct(product) {
  const res = await axios.post(
    `https://${process.env.SHOPIFY_STORE}/admin/api/2023-01/products.json`,
    { product },
    {
      headers: {
        "X-Shopify-Access-Token": process.env.SHOPIFY_ADMIN_TOKEN,
        "Content-Type": "application/json"
      }
    }
  );
  return res.data.product;
}

// === Supplier Modules ===
const suppliers = [
  {
    name: "CJdropshipping",
    fetchCatalog: async () => {
      const res = await axios.get("https://api.cjdropshipping.com/products", {
        headers: { "Authorization": `Bearer ${process.env.CJ_API_KEY}` }
      });

      return res.data.products.map(p => ({
        name: p.title,
        description: p.description,
        sku: p.sku,
        cost: p.cost,
        stock: p.stock,
        images: p.images
      }));
    }
  },

  {
    name: "Zendrop",
    fetchCatalog: async () => {
      console.log("[Jarvis] Zendrop support coming soon...");
      return [];
    }
  },

  {
    name: "Spocket",
    fetchCatalog: async () => {
      console.log("[Jarvis] Spocket support coming soon...");
      return [];
    }
  },

  {
    name: "Alibaba",
    fetchCatalog: async () => {
      console.log("[Jarvis] Alibaba support reserved for verified B2B accounts...");
      return [];
    }
  }
];

// === Main Import Engine ===
async function importAllProducts() {
  console.log("\\n[Jarvis] Initiating multi-supplier product import...");

  for (const supplier of suppliers) {
    try {
      console.log(`\\n→ Fetching catalog from ${supplier.name}...`);
      const products = await supplier.fetchCatalog();

      for (const product of products) {
        const { category, subcategory, tags } = categorizeProduct(product);

        const shopifyProduct = {
          title: product.name,
          body_html: product.description,
          vendor: supplier.name,
          product_type: category,
          tags: [...tags, subcategory],
          variants: [
            {
              price: (product.cost * 1.5).toFixed(2),
              sku: product.sku,
              inventory_quantity: product.stock,
              inventory_management: "shopify"
            }
          ],
          images: product.images.map(img => ({ src: img }))
        };

        try {
          await createShopifyProduct(shopifyProduct);
          console.log(`[✅ Uploaded] ${product.name}`);
        } catch (err) {
          console.error(`[❌ Shopify Error] ${product.name} — ${err.message}`);
        }
      }
    } catch (e) {
      console.error(`[❌ Failed to fetch from ${supplier.name}]`, e.message);
    }
  }

  console.log("\\n[Jarvis] Multi-supplier import complete.");
}

importAllProducts();
SHOPIFY_STORE=yourstore.myshopify.com
SHOPIFY_ADMIN_TOKEN=your-shopify-admin-token
CJ_API_KEY=your-cj-api-token

/**
 * JARVIS AI Swarm Engine for Shopify Store Automation
 * Includes customer AI agents + multi-platform social media poster
 */

const axios = require('axios');
const schedule = require('node-schedule');
require('dotenv').config();

/**
 * === AI Customer Agent (Handles Inquiries & Feedback) ===
 */
function handleCustomerMessage(message) {
  const lower = message.toLowerCase();

  if (lower.includes("where is my order")) return "Hi! You can track your order here: https://yourstore.com/track-order";
  if (lower.includes("refund") || lower.includes("return")) return "Returns and refunds follow the supplier's policy. Here's the link: https://yourstore.com/refund-policy";
  if (lower.includes("broken") || lower.includes("damaged")) return "We're sorry to hear that. Please send us a photo and we’ll help right away.";
  return "Thanks for reaching out! One of our team will reply within 24 hours.";
}

/**
 * === Social Media Content Generator (with SEO/AEO Keywords) ===
 */
function generatePost(product, platform) {
  const keyword = product.title.toLowerCase().includes("necklace") ? "#fashion" : "#trending";
  const seo = ["#shopify", "#onlinestore", "#viral", `#${platform.toLowerCase()}`, "#aishopify"];
  const base = `🔥 Just dropped! ${product.title} is now available. Tap the link in bio to shop now!`;

  return {
    text: `${base} ${keyword} ${seo.join(" ")}`,
    image: product.images[0] || "https://yourstore.com/default-image.jpg"
  };
}

/**
 * === Posting to Social Media Platforms (Mock Functions) ===
 * Replace with actual API integrations like Facebook Graph, TikTok, etc.
 */
function postToPlatform(platform, postContent) {
  console.log(`[📡 Posting to ${platform}]`);
  console.log("Text:", postContent.text);
  console.log("Image:", postContent.image);
  // Integration with APIs would go here
}

/**
 * === Scheduled Posting (10x Daily at Optimal Times) ===
 */
const platforms = ["Facebook", "Instagram", "TikTok", "YouTube", "Pinterest", "X", "LinkedIn", "Threads", "Snapchat", "Tumblr"];
const exampleProduct = {
  title: "Crystal Pendant Necklace",
  images: ["https://yourstore.com/products/necklace.jpg"]
};

function scheduleAllPosts() {
  const times = ["09:00", "10:30", "12:00", "13:30", "15:00", "16:30", "18:00", "19:30", "21:00", "22:30"];

  for (let i = 0; i < 10; i++) {
    const [hour, minute] = times[i].split(":").map(Number);
    const platform = platforms[i % platforms.length];
    const post = generatePost(exampleProduct, platform);

    schedule.scheduleJob({ hour, minute }, () => {
      postToPlatform(platform, post);
    });
  }

  console.log("[✅ Jarvis Scheduler] All 10 daily posts scheduled.");
}

scheduleAllPosts();

/**
 * === Handle Incoming Customer Events (e.g. live chat, email, form) ===
 */
function handleCustomerEvent(inputMessage) {
  const response = handleCustomerMessage(inputMessage);
  console.log("[🤖 AI Agent Responds]:", response);
}
npm install axios node-schedule dotenv
node your-filename.js
const axios = require('axios');

async function generateSmartCaption(product) {
  const prompt = `Write a short, catchy, SEO-optimized social media caption to promote this product:
Title: ${product.title}
Category: ${product.category}
Features: ${product.description.slice(0, 100)}...`;

  const response = await axios.post(
    "https://api.openai.com/v1/chat/completions",
    {
      model: "gpt-4",
      messages: [
        { role: "system", content: "You are a viral social media expert." },
        { role: "user", content: prompt }
      ],
      temperature: 0.8,
      max_tokens: 100
    },
    {
      headers: {
        Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": "application/json"
      }
    }
  );

  return response.data.choices[0].message.content;
}

module.exports = { generateSmartCaption };
const axios = require('axios');

async function translatePost(text, targetLang) {
  const response = await axios.post("https://libretranslate.de/translate", {
    q: text,
    source: "en",
    target: targetLang,
    format: "text"
  }, {
    headers: { "Content-Type": "application/json" }
  });

  return response.data.translatedText;
}

module.exports = { translatePost };
const axios = require('axios');

async function postToFacebook(text, image_url) {
  const pageAccessToken = process.env.FB_PAGE_TOKEN;
  const pageID = process.env.FB_PAGE_ID;

  const response = await axios.post(
    `https://graph.facebook.com/${pageID}/photos`,
    {
      url: image_url,
      caption: text,
      access_token: pageAccessToken
    }
  );

  return response.data;
}

async function postToTikTok(video_url, text) {
  console.log("[Mock] TikTok post:", video_url, "|", text);
  return { success: true };
}

module.exports = { postToFacebook, postToTikTok };
const axios = require('axios');

async function postToInstagram(image_url, caption) {
  const igUserId = process.env.IG_USER_ID;
  const igAccessToken = process.env.IG_ACCESS_TOKEN;

  const createRes = await axios.post(`https://graph.facebook.com/v17.0/${igUserId}/media`, {
    image_url,
    caption,
    access_token: igAccessToken
  });

  const containerId = createRes.data.id;

  const publishRes = await axios.post(`https://graph.facebook.com/v17.0/${igUserId}/media_publish`, {
    creation_id: containerId,
    access_token: igAccessToken
  });

  return publishRes.data;
}

module.exports = { postToInstagram };
function generatePromoVideo(product, caption) {
  console.log("[🎥] Generating AI Promo Video for:", product.title);
  return {
    video_url: "https://yourcdn.com/videos/generated-promo.mp4",
    caption
  };
}

module.exports = { generatePromoVideo };
const express = require('express');
const { generateSmartCaption } = require('./agent-captions');
const { generatePromoVideo } = require('./agent-video');
const { postToFacebook, postToTikTok } = require('./agent-posting');
const { postToInstagram } = require('./agent-instagram');
const { translatePost } = require('./agent-translate');

const app = express();
app.use(express.json());

app.post('/webhook/product-created', async (req, res) => {
  const product = req.body.product;

  console.log("[🔔] Shopify Product Created Triggered");
  const caption = await generateSmartCaption(product);
  const translated = await translatePost(caption, "es");
  const promo = generatePromoVideo(product, translated);

  await postToFacebook(translated, product.image);
  await postToInstagram(product.image, translated);
  await postToTikTok(promo.video_url, translated);

  res.status(200).send("Posted successfully");
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`[🚀 Jarvis Webhook Listening on port ${PORT}]`);
});
OPENAI_API_KEY=your-openai-key
FB_PAGE_TOKEN=your-facebook-page-access-token
FB_PAGE_ID=your-facebook-page-id
IG_USER_ID=your-instagram-user-id
IG_ACCESS_TOKEN=your-instagram-token
PORT=3000
npm install axios express dotenv
POST https://your-domain.com/webhook/product-created

// YouTube Shorts Auto-Uploader (Mock)
// Replace with YouTube Data API v3 for real deployment

async function postToYouTube(video_url, title, description) {
  console.log("[🎬 YouTube] Uploading video...");
  console.log("Title:", title);
  console.log("Description:", description);
  console.log("Video URL:", video_url);
  return { status: "uploaded", platform: "YouTube" };
}

module.exports = { postToYouTube };
// LinkedIn API Post (Mock)
// Use LinkedIn OAuth2 and /ugcPosts endpoint for real posts

async function postToLinkedIn(text, image_url) {
  console.log("[💼 LinkedIn] Posting update...");
  console.log("Text:", text);
  console.log("Image:", image_url);
  return { status: "posted", platform: "LinkedIn" };
}

module.exports = { postToLinkedIn };
// Threads (Meta) Poster via Instagram proxy (Mock)

async function postToThreads(text, image_url) {
  console.log("[🧵 Threads] Posting content via Instagram API...");
  console.log("Caption:", text);
  console.log("Image:", image_url);
  return { status: "posted", platform: "Threads" };
}

module.exports = { postToThreads };
// Reddit Poster (Mock)
// Use Reddit's API with OAuth2 or snoowrap for real integration

async function postToReddit(title, url) {
  console.log("[👽 Reddit] Submitting post...");
  console.log("Title:", title);
  console.log("URL:", url);
  return { status: "posted", platform: "Reddit" };
}

module.exports = { postToReddit };
// Pinterest API Pin Poster (Mock)
// Use Pinterest Developer API for real pin creation

async function postToPinterest(title, image_url, link) {
  console.log("[📌 Pinterest] Creating new pin...");
  console.log("Title:", title);
  console.log("Image:", image_url);
  console.log("Link:", link);
  return { status: "pinned", platform: "Pinterest" };
}

module.exports = { postToPinterest };
// Discord Poster via Webhook

const axios = require('axios');

async function postToDiscord(text, image_url) {
  const webhookUrl = process.env.DISCORD_WEBHOOK_URL;

  await axios.post(webhookUrl, {
    content: text,
    embeds: [{
      image: { url: image_url }
    }]
  });

  console.log("[🎮 Discord] Message sent successfully.");
  return { status: "posted", platform: "Discord" };
}

module.exports = { postToDiscord };
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
YOUTUBE_API_KEY=your-youtube-key
LINKEDIN_ACCESS_TOKEN=your-linkedin-token
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USERNAME=...
REDDIT_PASSWORD=...
PINTEREST_ACCESS_TOKEN=...
const {
  generateSmartCaption
} = require('./agent-captions');
const {
  generatePromoVideo
} = require('./agent-video');
const {
  translatePost
} = require('./agent-translate');
const {
  postToFacebook,
  postToTikTok
} = require('./agent-posting');
const {
  postToInstagram
} = require('./agent-instagram');
const {
  postToThreads
} = require('./agent-threads');
const {
  postToYouTube
} = require('./agent-youtube');
const {
  postToLinkedIn
} = require('./agent-linkedin');
const {
  postToReddit
} = require('./agent-reddit');
const {
  postToPinterest
} = require('./agent-pinterest');
const {
  postToDiscord
} = require('./agent-discord');

const schedule = require('node-schedule');

const product = {
  title: "AI-Powered Home Massage Gun",
  description: "Powerful, deep tissue, intelligent percussive therapy device with 6 speeds and 4 heads.",
  category: "Wellness",
  image: "https://yourcdn.com/products/massage-gun.jpg"
};

const scheduleTimes = [
  "09:00", "10:30", "12:00", "13:30", "15:00",
  "16:30", "18:00", "19:30", "21:00", "22:30"
];

function scheduleJarvisSwarm() {
  scheduleTimes.forEach((timeStr, index) => {
    const [hour, minute] = timeStr.split(":").map(Number);

    schedule.scheduleJob({ hour, minute }, async () => {
      console.log(`\n[⏰ ${timeStr}] Jarvis AI Swarm Activated`);

      const caption = await generateSmartCaption(product);
      const translated = await translatePost(caption, "es");
      const promo = generatePromoVideo(product, translated);

      await Promise.all([
        postToFacebook(translated, product.image),
        postToInstagram(product.image, translated),
        postToThreads(translated, product.image),
        postToTikTok(promo.video_url, translated),
        postToYouTube(promo.video_url, product.title, translated),
        postToLinkedIn(translated, product.image),
        postToReddit(product.title, product.image),
        postToPinterest(product.title, product.image, "https://yourstore.com/products/massage-gun"),
        postToDiscord(translated, product.image)
      ]);

      console.log("[✅ All Platforms Posted]");
    });
  });

  console.log("[🚀 Jarvis Unified Swarm Scheduler Deployed]");
}

scheduleJarvisSwarm();
node jarvis-unified-swarm-scheduler.js
const axios = require('axios');

async function getShopifyProducts() {
  const storeUrl = process.env.SHOPIFY_STORE_URL;
  const accessToken = process.env.SHOPIFY_ADMIN_TOKEN;

  const response = await axios.get(`https://${storeUrl}/admin/api/2023-07/products.json`, {
    headers: {
      "X-Shopify-Access-Token": accessToken
    }
  });

  return response.data.products.map(product => ({
    title: product.title,
    description: product.body_html.replace(/<[^>]*>?/gm, ''),
    image: product.images[0]?.src || '',
    id: product.id
  }));
}

module.exports = { getShopifyProducts };
// CJ Dropshipping mock video retriever
// Replace with their API once available

async function getCJVideoForProduct(product) {
  const slug = product.title.toLowerCase().replace(/\\s+/g, '-');
  return {
    video_url: `https://video.cjdropshipping.com/assets/${slug}.mp4`
  };
}

module.exports = { getCJVideoForProduct };
const { generateSmartCaption } = require('./agent-captions');
const { translatePost } = require('./agent-translate');
const {
  postToFacebook,
  postToInstagram,
  postToThreads,
  postToTikTok,
  postToYouTube,
  postToLinkedIn,
  postToReddit,
  postToPinterest,
  postToDiscord
} = require('./agent-posting-modules');

async function postMultilingual(product, video_url) {
  const caption = await generateSmartCaption(product);

  const languages = ['en', 'es', 'fr', 'de', 'zh']; // You can expand this list
  const translations = await Promise.all(
    languages.map(lang => translatePost(caption, lang))
  );

  for (const text of translations) {
    await Promise.all([
      postToFacebook(text, product.image),
      postToInstagram(product.image, text),
      postToThreads(text, product.image),
      postToTikTok(video_url, text),
      postToYouTube(video_url, product.title, text),
      postToLinkedIn(text, product.image),
      postToReddit(product.title, product.image),
      postToPinterest(product.title, product.image, "https://yourstore.com/products/" + product.id),
      postToDiscord(text, product.image)
    ]);
  }
}

module.exports = { postMultilingual };
const { getShopifyProducts } = require('./shopify-products');
const { getCJVideoForProduct } = require('./cj-videos');
const { postMultilingual } = require('./multilingual-loop');
const schedule = require('node-schedule');

function scheduleFullAutomation() {
  schedule.scheduleJob('0 6 * * *', async () => {
    console.log("[⏰ Jarvis Full Auto Scheduler Triggered]");
    const products = await getShopifyProducts();

    for (const product of products.slice(0, 3)) {
      const video = await getCJVideoForProduct(product);
      await postMultilingual(product, video.video_url);
    }

    console.log("[✅ Daily Auto Posting Complete]");
  });

  console.log("[🚀 Jarvis Full Automation Deployed – Posts Daily at 6AM]");
}

scheduleFullAutomation();
npm install axios dotenv node-schedule
SHOPIFY_STORE_URL=yourstore.myshopify.com
SHOPIFY_ADMIN_TOKEN=your_shopify_admin_token
node full-auto-scheduler.js
const axios = require('axios');

// CJ Dropshipping pull (mocked structure for demo)
async function pullCJProducts() {
  const cjProducts = await axios.get('https://mock.cjdropshipping.api/products');
  return cjProducts.data.map(p => ({
    title: p.name,
    description: p.description,
    image: p.image_url,
    price: p.price,
    supplier: 'CJ',
    sku: p.sku
  }));
}

// Future Supplier Integration Example
async function pullOtherSupplierProducts() {
  const otherProducts = []; // Replace with real API logic
  return otherProducts.map(p => ({
    title: p.title,
    description: p.desc,
    image: p.image,
    price: p.price,
    supplier: 'AliExpress',
    sku: p.sku
  }));
}

async function getAllSupplierProducts() {
  const cj = await pullCJProducts();
  const others = await pullOtherSupplierProducts();
  return [...cj, ...others];
}

module.exports = { getAllSupplierProducts };
function categorizeProduct(product) {
  const title = product.title.toLowerCase();
  const description = product.description.toLowerCase();

  if (title.includes("earbuds") || description.includes("bluetooth")) return "Electronics > Audio";
  if (title.includes("lamp") || description.includes("light")) return "Home & Living > Lighting";
  if (title.includes("toy") || description.includes("child")) return "Kids & Toys";
  if (title.includes("shirt") || title.includes("hoodie")) return "Fashion > Apparel";
  if (title.includes("necklace") || title.includes("jewelry")) return "Accessories > Jewelry";

  return "General > Misc";
}

module.exports = { categorizeProduct };
const axios = require('axios');

const SHOPIFY_URL = process.env.SHOPIFY_STORE_URL;
const SHOPIFY_TOKEN = process.env.SHOPIFY_ADMIN_TOKEN;

async function ensureCollection(categoryName) {
  const url = `https://${SHOPIFY_URL}/admin/api/2023-07/custom_collections.json`;

  const existing = await axios.get(url, {
    headers: { "X-Shopify-Access-Token": SHOPIFY_TOKEN }
  });

  const found = existing.data.custom_collections.find(c => c.title === categoryName);
  if (found) return found.id;

  const created = await axios.post(url, {
    custom_collection: { title: categoryName }
  }, {
    headers: { "X-Shopify-Access-Token": SHOPIFY_TOKEN }
  });

  return created.data.custom_collection.id;
}

async function uploadToShopify(product, category) {
  const collectionId = await ensureCollection(category);

  const url = `https://${SHOPIFY_URL}/admin/api/2023-07/products.json`;
  const response = await axios.post(url, {
    product: {
      title: product.title,
      body_html: product.description,
      vendor: product.supplier,
      tags: [category],
      images: [{ src: product.image }],
      variants: [{
        price: product.price,
        sku: product.sku
      }]
    }
  }, {
    headers: { "X-Shopify-Access-Token": SHOPIFY_TOKEN }
  });

  return response.data.product;
}

module.exports = { uploadToShopify };
function generateTags(description) {
  const words = description.toLowerCase().match(/\\b[a-z]{4,}\\b/g) || [];
  const freq = {};
  for (const word of words) {
    freq[word] = (freq[word] || 0) + 1;
  }
  const tags = Object.keys(freq).sort((a, b) => freq[b] - freq[a]).slice(0, 10);
  return [...new Set(tags)];
}

module.exports = { generateTags };
const { getAllSupplierProducts } = require('./supplier-pull');
const { categorizeProduct } = require('./auto-categorizer');
const { uploadToShopify } = require('./shopify-uploader');
const { generateTags } = require('./tag-normalizer');

(async () => {
  console.log("🚀 Starting full supplier-to-Shopify automation");

  const products = await getAllSupplierProducts();

  for (const product of products) {
    const category = categorizeProduct(product);
    const tags = generateTags(product.description);
    product.description += `<br><br><b>Tags:</b> ${tags.join(', ')}`;
    await uploadToShopify(product, category);
    console.log(`✅ Uploaded: ${product.title} to ${category}`);
  }

  console.log("🎯 All products imported and categorized.");
})();
npm install axios dotenv
SHOPIFY_STORE_URL=your-store.myshopify.com
SHOPIFY_ADMIN_TOKEN=your-admin-access-token
const { Configuration, OpenAIApi } = require("openai");

const configuration = new Configuration({
  apiKey: process.env.OPENAI_API_KEY
});
const openai = new OpenAIApi(configuration);

async function generateSEOKeywords(product) {
  const prompt = `
  Write a list of 15 high-conversion SEO and AEO keywords and long-tail phrases for this product:

  Product Title: ${product.title}
  Product Description: ${product.description}
  
  The keywords must:
  - Be specific to the product
  - Be phrased like search engine or voice queries
  - Be optimized for TikTok, Google, Perplexity, YouTube, and ChatGPT-based shopping assistants

  Return them as a clean, comma-separated list only.
  `;

  const completion = await openai.createChatCompletion({
    model: "gpt-4",
    messages: [{ role: "user", content: prompt }],
    max_tokens: 150
  });

  const keywords = completion.data.choices[0].message.content.trim();
  return keywords.split(",").map(k => k.trim());
}

module.exports = { generateSEOKeywords };
const { generateSEOKeywords } = require('./agent-seo');

// Inside your main for-loop:
for (const product of products) {
  const category = categorizeProduct(product);
  const aiTags = await generateSEOKeywords(product);
  const seoText = `<br><br><b>Search Terms:</b> ${aiTags.join(', ')}`;
  product.description += seoText;

  product.tags = aiTags; // Optional: include in Shopify tags
  await uploadToShopify(product, category);
  console.log(`✅ Uploaded: ${product.title} to ${category} with SEO/AEO`);
}
OPENAI_API_KEY=sk-...
const { generateSEOKeywords } = require('./agent-seo');
async function postMultilingual(product, video_url) {
  const caption = await generateSmartCaption(product);
  const seoTags = await generateSEOKeywords(product);
  const searchTags = `\\n\\n🔎 Keywords: ${seoTags.slice(0, 10).join(", ")}`;
  const fullCaption = `${caption}${searchTags}`;

  const languages = ['en', 'es', 'fr', 'de', 'zh'];
  const translations = await Promise.all(
    languages.map(lang => translatePost(fullCaption, lang))
  );

  for (const text of translations) {
    await Promise.all([
      postToFacebook(text, product.image),
      postToInstagram(product.image, text),
      postToThreads(text, product.image),
      postToTikTok(video_url, text),
      postToYouTube(video_url, product.title, text),
      postToLinkedIn(text, product.image),
      postToReddit(product.title, product.image),
      postToPinterest(product.title, product.image, "https://yourstore.com/products/" + product.id),
      postToDiscord(text, product.image)
    ]);
  }
}
function generateSchema(product) {
  return `
  <script type="application/ld+json">
  {
    "@context": "https://schema.org/",
    "@type": "Product",
    "name": "${product.title}",
    "image": ["${product.image}"],
    "description": "${product.description.replace(/"/g, '\\"')}",
    "sku": "${product.sku}",
    "brand": {
      "@type": "Organization",
      "name": "${product.supplier}"
    },
    "offers": {
      "@type": "Offer",
      "url": "https://yourstore.com/products/${product.id}",
      "priceCurrency": "NZD",
      "price": "${product.price}",
      "availability": "https://schema.org/InStock"
    }
  }
  </script>
  `;
}
const schemaMarkup = generateSchema(product);
product.description += `\\n\\n${schemaMarkup}`;
<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:g="http://base.google.com/ns/1.0" version="2.0">
  <channel>
    <title>Your Store Name</title>
    <link>https://yourstore.com</link>
    <description>Full inventory feed for Google Merchant Center</description>

    {% for product in collections.all.products %}
    <item>
      <g:id>{{ product.id }}</g:id>
      <g:title>{{ product.title | escape }}</g:title>
      <g:description>{{ product.description | strip_html | escape }}</g:description>
      <g:link>{{ shop.url }}/products/{{ product.handle }}</g:link>
      <g:image_link>{{ product.featured_image.src | img_url: 'master' }}</g:image_link>
      <g:availability>in stock</g:availability>
      <g:price>{{ product.variants.first.price | money_without_currency }} NZD</g:price>
      <g:brand>{{ product.vendor }}</g:brand>
      <g:condition>new</g:condition>
    </item>
    {% endfor %}
  </channel>
</rss>
https://yourstore.com/google-merchant-feed
{% if product %}
  <meta property="og:type" content="product">
  <meta property="og:title" content="{{ product.title }}">
  <meta property="og:description" content="{{ product.description | strip_html | truncate: 200 }}">
  <meta property="og:image" content="{{ product.featured_image | img_url: 'master' }}">
  <meta property="og:url" content="{{ shop.url }}/products/{{ product.handle }}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{{ product.title }}">
  <meta name="twitter:description" content="{{ product.description | strip_html | truncate: 200 }}">
  <meta name="twitter:image" content="{{ product.featured_image | img_url: 'master' }}">
{% endif %}
const metaKeywords = aiTags.join(", ");
product.description += `<meta name="keywords" content="${metaKeywords}">`;
/bing-shopping-feed.liquid
<rss xmlns:g="http://schemas.microsoft.com/ads/2009/06/catalog" version="2.0">
<rss version="2.0">
  <channel>
    <title>Your Store</title>
    <link>https://yourstore.com</link>
    <description>Meta Catalog</description>
    {% for product in collections.all.products %}
    <item>
      <id>{{ product.id }}</id>
      <title>{{ product.title | escape }}</title>
      <description>{{ product.description | strip_html | escape }}</description>
      <availability>in stock</availability>
      <condition>new</condition>
      <price>{{ product.variants.first.price | money_without_currency }} NZD</price>
      <link>{{ shop.url }}/products/{{ product.handle }}</link>
      <image_link>{{ product.featured_image.src | img_url: 'master' }}</image_link>
      <brand>{{ product.vendor }}</brand>
    </item>
    {% endfor %}
  </channel>
</rss>
app.post('/webhooks/products/create', async (req, res) => {
  const product = req.body;

  // Trigger keyword generation + AEO
  const seoTags = await generateSEOKeywords(product);
  product.tags = seoTags;

  // Upload to Google/Bing/Meta feed queue
  await uploadToShopify(product, categorizeProduct(product));

  res.status(200).send('✅ Product sync complete.');
});
POST /admin/api/2023-07/webhooks.json
📂 /jarvis-commerce-sync
├── server.js
├── routes/
│   ├── /products/create (webhook handler)
│   ├── /feeds/google
│   ├── /feeds/bing
│   └── /feeds/facebook
├── /scripts/
│   ├── generateSEOKeywords.js
│   ├── categorizeProduct.js
│   └── uploadToShopify.js
└── .env
complete-drop-ship-app/
├─ .env.example
├─ package.json
├─ server.js
├─ /webhooks.js
├─ /oauth.js
├─ /shopify.js
├─ /feeds.js
├─ /billing.js
├─ /ai/
│   ├─ agent-categorizer.js
│   ├─ agent-seo.js
│   ├─ agent-caption.js
│   ├─ agent-translate.js
│   └─ agent-social.js
└─ /scheduler.js
{
  "name": "complete-drop-ship-automation",
  "version": "1.0.0",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "schedule": "node scheduler.js"
  },
  "dependencies": {
    "axios": "^1.6.0",
    "dotenv": "^16.0.3",
    "express": "^4.18.2",
    "node-schedule": "^2.1.0",
    "openai": "^4.5.0",
    "stripe": "^12.0.0",
    "@shopify/koa-shopify-auth": "*",
    "@shopify/koa-shopify-webhooks": "*",
    "koa": "^2.14.1",
    "koa-router": "^12.0.0",
    "koa-session": "^6.1.0"
  }
}
SHOPIFY_API_KEY=your_shopify_api_key
SHOPIFY_API_SECRET=your_shopify_secret
SHOPIFY_SCOPES=read_products,write_products,read_content,write_content
SHOPIFY_APP_URL=https://your-app-url.com
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
OPENAI_API_KEY=sk-...
METAFIELD_NAMESPACE=custom
require('dotenv').config();
const Koa = require('koa'), Router = require('koa-router'), session = require('koa-session');
const shopifyAuth = require('@shopify/koa-shopify-auth').default;
const { default: createShopifyAuth } = require('@shopify/koa-shopify-auth');
const { receiveWebhook } = require('@shopify/koa-shopify-webhooks');
const billing = require('./billing');
const webhooks = require('./webhooks');
const feeds = require('./feeds');

const app = new Koa();
const router = new Router();
app.keys = [process.env.SHOPIFY_API_SECRET];
app.use(session(app));

app.use(createShopifyAuth({
  apiKey: process.env.SHOPIFY_API_KEY,
  secret: process.env.SHOPIFY_API_SECRET,
  scopes: process.env.SHOPIFY_SCOPES.split(","),
  afterAuth: async (ctx) => {
    const { shop, accessToken } = ctx.session;
    // Register webhooks
    await webhooks.registerProductWebhooks(shop, accessToken);
    // Save shop info to database (optional)
    ctx.redirect('/');
  }
}));

const webhook = receiveWebhook({ secret: process.env.SHOPIFY_API_SECRET });
router.post('/webhooks/products/create', webhook, async (ctx) => {
  await webhooks.handleProductCreate(ctx.request.body);
  ctx.status = 200;
});
router.post('/webhooks/products/update', webhook, async (ctx) => {
  await webhooks.handleProductCreate(ctx.request.body);
  ctx.status = 200;
});

router.get('/feeds/google', async (ctx) => feeds.google(ctx));
router.get('/feeds/bing', async (ctx) => feeds.bing(ctx));
router.get('/feeds/meta', async (ctx) => feeds.meta(ctx));
router.get('/feeds/tiktok', async (ctx) => feeds.tiktok(ctx));
router.get('/feeds/pinterest', async (ctx) => feeds.pinterest(ctx));

app.use(router.routes());
app.use(router.allowedMethods());

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`⚙️ App running on port ${PORT}`));
const shopify = require('./shopify');
const ai = require('./ai/agent-seo');
const categorizer = require('./ai/agent-categorizer');

async function registerProductWebhooks(shop, token) {
  await shopify.registerWebhook(shop, token, 'products/create', '/webhooks/products/create');
  await shopify.registerWebhook(shop, token, 'products/update', '/webhooks/products/update');
}
async function handleProductCreate(product) {
  const category = categorizer.categorizeProduct(product);
  const seoTags = await ai.generateSEOKeywords({ title: product.title, description: product.body_html });
  await shopify.updateProductMetadata(product.id, category, seoTags);
}
module.exports = { registerProductWebhooks, handleProductCreate };
const axios = require('axios');
const Shopify = require('koa-shopify-graphql-proxy');

async function registerWebhook(shop, token, topic, path) {
  await axios.post(`https://${shop}/admin/api/2023-07/webhooks.json`, {
    webhook: { topic, address: process.env.SHOPIFY_APP_URL + path, format: 'json' }
  }, { headers: { "X-Shopify-Access-Token": token }});
}
async function updateProductMetadata(productId, collectionTitle, seoTags) {
  const url = `https://${shop}/admin/api/2023-07/products/${productId}.json`;
  await axios.put(url, {
    product: {
      id: productId,
      tags: seoTags,
      metafields: [{
        namespace: process.env.METAFIELD_NAMESPACE,
        key: 'collection',
        value: collectionTitle,
        type: 'single_line_text_field'
      }]
    }
  }, { headers: { "X-Shopify-Access-Token": token } });
}
module.exports = { registerWebhook, updateProductMetadata };
const liquid = require('liquidjs')();
const fs = require('fs');
async function renderTemplate(name, ctx) {
  const tpl = fs.readFileSync(__dirname + `/templates/${name}.liquid`, 'utf8');
  return liquid.parseAndRender(tpl, ctx);
}
module.exports = {
  google: async ctx => ctx.body = await renderTemplate('google-merchant-feed', ctx),
  bing: async ctx => ctx.body = await renderTemplate('bing-shopping-feed', ctx),
  meta: async ctx => ctx.body = await renderTemplate('facebook-catalog-feed', ctx),
  tiktok: async ctx => { /* future */}
  pinterest: async ctx => { /* future */}
};
const Stripe = require('stripe');
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

const plans = {
  pro: 'price_123abc',       // from Stripe Dashboard
  elite: 'price_456def'
};

async function requireSubscription(ctx, next) {
  const tier = ctx.session.tier;
  if (tier === 'free') return next();
  const subscription = await stripe.subscriptions.retrieve(ctx.session.subId);
  if (subscription.status !== 'active') ctx.throw(402, 'Payment Required');
  return next();
}
module.exports = { stripe, plans, requireSubscription };
const schedule = require('node-schedule');
const shopifyProducts = require('./shopify').fetchAllProducts;
const ai = require('./ai/agent-caption');
const social = require('./ai/agent-social');
const translate = require('./ai/agent-translate');

schedule.scheduleJob('0 8 * * *', async () => {
  const products = await shopifyProducts();
  for (const p of products) {
    const caption = await ai.generateSmartCaption(p);
    const langs = ['en','es','fr'];
    for (const lang of langs) {
      const text = await translate.translatePost(caption, lang);
      await social.postToAll(p, text);
    }
  }
});
MASTER_HASH=$2b$10$5c47vF3KHyDPSnXZhNziL..b6XOblPgq3xeWvcZB15RAcAGj9OkRq
const Stripe = require('stripe');
const bcrypt = require('bcrypt');
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

const plans = {
  pro: 'price_123abc',     // Replace with your real Stripe price ID
  elite: 'price_456def'
};

async function requireSubscription(ctx, next) {
  const submittedCode = ctx.headers['x-master-code'] || ctx.cookies.get('master');
  const isValid = submittedCode 
    ? await bcrypt.compare(submittedCode, process.env.MASTER_HASH)
    : false;

  if (isValid) {
    console.log("🟢 Master Access Granted");
    return next(); // skip billing checks
  }

  const tier = ctx.session.tier;
  if (tier === 'free') return next();

  const subscription = await stripe.subscriptions.retrieve(ctx.session.subId);
  if (subscription.status !== 'active') ctx.throw(402, 'Payment Required');

  return next();
}

module.exports = { stripe, plans, requireSubscription };
router.get('/admin', async (ctx) => {
  ctx.body = `
    <html>
      <body>
        <h2>🔒 Enter Admin Access Code</h2>
        <form method="POST" action="/admin">
          <input name="code" type="password" placeholder="Enter code" />
          <button type="submit">Unlock</button>
        </form>
      </body>
    </html>
  `;
});

router.post('/admin', async (ctx) => {
  const body = await new Promise((resolve) => {
    let data = '';
    ctx.req.on('data', (chunk) => (data += chunk));
    ctx.req.on('end', () => resolve(Object.fromEntries(new URLSearchParams(data))));
  });

  const bcrypt = require('bcrypt');
  const isValid = await bcrypt.compare(body.code, process.env.MASTER_HASH);

  if (isValid) {
    ctx.cookies.set('master', body.code, { httpOnly: true });
    ctx.redirect('/');
  } else {
    ctx.body = '❌ Incorrect Code. <a href="/admin">Try Again</a>';
  }
});
const submittedCode = ctx.headers['x-master-code'] || ctx.cookies.get('master');
<a href="/admin" style="opacity:0.3;font-size:10px;">🔒 Admin Access</a>
<div id="admin-badge" style="position:fixed;top:10px;right:10px;z-index:9999;display:none;">
  <span style="padding:5px 10px;background:linear-gradient(90deg,#0f0,#4caf50);color:white;
  border-radius:5px;font-weight:bold;box-shadow:0 0 8px #0f0;animation: pulse 1.5s infinite;">
    ADMIN MODE
  </span>
</div>

<style>
@keyframes pulse {
  0% { box-shadow: 0 0 5px #0f0; }
  50% { box-shadow: 0 0 15px #0f0; }
  100% { box-shadow: 0 0 5px #0f0; }
}
</style>

<script>
  if (document.cookie.includes("master=JarvisOverlord999")) {
    document.getElementById("admin-badge").style.display = "block";
  }
</script>
<html>
<head>
  <title>🔐 Admin Unlock</title>
  <style>
    body {
      font-family: 'Segoe UI', sans-serif;
      background: radial-gradient(#222, #000);
      color: white;
      text-align: center;
      padding-top: 15%;
    }
    .card {
      background: rgba(255,255,255,0.05);
      padding: 30px;
      border-radius: 15px;
      display: inline-block;
      box-shadow: 0 0 10px rgba(0,255,0,0.3);
      animation: glow 2s infinite;
    }
    input {
      padding: 10px;
      border-radius: 5px;
      border: none;
      width: 250px;
      margin-bottom: 15px;
    }
    button {
      padding: 10px 20px;
      background: #00ff00;
      color: black;
      border: none;
      font-weight: bold;
      border-radius: 5px;
      cursor: pointer;
    }
    @keyframes glow {
      0% { box-shadow: 0 0 5px #0f0; }
      50% { box-shadow: 0 0 20px #0f0; }
      100% { box-shadow: 0 0 5px #0f0; }
    }
  </style>
</head>
<body>
  <div class="card">
    <h2>🔒 ADMIN PORTAL</h2>
    <form method="POST" action="/admin">
      <input type="password" name="code" placeholder="Enter secret God Code"/><br/>
      <button type="submit">Unlock</button>
    </form>
  </div>
</body>
</html>
ctx.cookies.set('master', body.code, { httpOnly: true });
ctx.redirect('/?admin=1');
<script>
if (new URLSearchParams(window.location.search).get("admin") === "1") {
  document.getElementById("admin-badge").style.display = "block";
}
</script>
const bcrypt = require('bcrypt');

router.get('/admin', async (ctx) => {
  ctx.body = `
    <html>
    <head>
      <title>🔐 Admin Portal</title>
      <style>
        body { background: radial-gradient(#222, #000); color: white; text-align: center; padding-top: 15%; font-family: sans-serif; }
        .card {
          background: rgba(255,255,255,0.05); padding: 30px; border-radius: 15px;
          display: inline-block; box-shadow: 0 0 10px rgba(0,255,0,0.3); animation: glow 2s infinite;
        }
        input { padding: 10px; width: 250px; border: none; border-radius: 5px; margin-top: 15px; }
        button {
          margin-top: 20px; padding: 10px 20px; background: #0f0; color: black;
          font-weight: bold; border: none; border-radius: 5px; cursor: pointer;
        }
        a { color: #0f0; text-decoration: none; font-size: 12px; display: block; margin-top: 10px; }
        @keyframes glow {
          0% { box-shadow: 0 0 5px #0f0; }
          50% { box-shadow: 0 0 20px #0f0; }
          100% { box-shadow: 0 0 5px #0f0; }
        }
      </style>
    </head>
    <body>
      <div class="card">
        <h2>🔒 Enter Admin Access Code</h2>
        <form method="POST" action="/admin">
          <input name="code" type="password" placeholder="Enter secret code" /><br/>
          <button type="submit">Unlock</button>
        </form>
        <a href="/">⬅ Back to App</a>
      </div>
    </body>
    </html>
  `;
});

router.post('/admin', async (ctx) => {
  const data = await new Promise(resolve => {
    let body = '';
    ctx.req.on('data', chunk => body += chunk);
    ctx.req.on('end', () => resolve(Object.fromEntries(new URLSearchParams(body))));
  });

  const isValid = await bcrypt.compare(data.code, process.env.MASTER_HASH);
  if (isValid) {
    ctx.cookies.set('master', data.code, { httpOnly: true });
    ctx.redirect('/?admin=1');
  } else {
    ctx.body = `<p style="color:red;text-align:center;">❌ Incorrect code</p><script>setTimeout(()=>{location.href='/admin'},2000)</script>`;
  }
});
<div id="admin-badge" style="position:fixed;top:10px;right:10px;z-index:9999;display:none;">
  <span style="padding:5px 10px;background:linear-gradient(90deg,#0f0,#4caf50);color:white;
  border-radius:5px;font-weight:bold;box-shadow:0 0 8px #0f0;animation: pulse 1.5s infinite;">
    ADMIN MODE
    <button onclick="logoutAdmin()" style="margin-left:10px;background:black;color:#0f0;
    border:none;padding:2px 6px;border-radius:4px;cursor:pointer;font-size:10px;">
      Logout
    </button>
  </span>
</div>

<style>
@keyframes pulse {
  0% { box-shadow: 0 0 5px #0f0; }
  50% { box-shadow: 0 0 15px #0f0; }
  100% { box-shadow: 0 0 5px #0f0; }
}
</style>

<script>
  function logoutAdmin() {
    document.cookie = "master=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    location.reload();
  }
  if (document.cookie.includes("master=JarvisOverlord999")) {
    document.getElementById("admin-badge").style.display = "block";
  }
</script>
require('dotenv').config();
const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const adminRoutes = require('./routes/admin');
const billingRoutes = require('./routes/billing');

const app = new Koa();
const router = new Router();

app.use(bodyParser());
router.use('/admin', adminRoutes.routes());
router.use('/billing', billingRoutes.routes());

app.use(router.routes()).use(router.allowedMethods());

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`✅ App running on port ${PORT}`);
});
PORT=3000
MASTER_HASH=$2b$10$5c47vF3KHyDPSnXZhNziL..b6XOblPgq3xeWvcZB15RAcAGj9OkRq
STRIPE_SECRET_KEY=sk_live_your_key_here
SHOPIFY_API_KEY=your_api_key_here
SHOPIFY_API_SECRET=your_api_secret_here
const Router = require('koa-router');
const bcrypt = require('bcrypt');
const router = new Router();

router.get('/', async (ctx) => {
  ctx.body = `
    <html>
    <head>
      <title>🔐 Admin Portal</title>
      <style>
        body { background: radial-gradient(#222, #000); color: white; text-align: center; padding-top: 15%; font-family: sans-serif; }
        .card {
          background: rgba(255,255,255,0.05); padding: 30px; border-radius: 15px;
          display: inline-block; box-shadow: 0 0 10px rgba(0,255,0,0.3); animation: glow 2s infinite;
        }
        input { padding: 10px; width: 250px; border: none; border-radius: 5px; margin-top: 15px; }
        button {
          margin-top: 20px; padding: 10px 20px; background: #0f0; color: black;
          font-weight: bold; border: none; border-radius: 5px; cursor: pointer;
        }
        a { color: #0f0; text-decoration: none; font-size: 12px; display: block; margin-top: 10px; }
        @keyframes glow {
          0% { box-shadow: 0 0 5px #0f0; }
          50% { box-shadow: 0 0 20px #0f0; }
          100% { box-shadow: 0 0 5px #0f0; }
        }
      </style>
    </head>
    <body>
      <div class="card">
        <h2>🔒 Enter Admin Access Code</h2>
        <form method="POST" action="/admin">
          <input name="code" type="password" placeholder="Enter secret code" /><br/>
          <button type="submit">Unlock</button>
        </form>
        <a href="/">⬅ Back to App</a>
      </div>
    </body>
    </html>
  `;
});

router.post('/', async (ctx) => {
  const data = await new Promise(resolve => {
    let body = '';
    ctx.req.on('data', chunk => body += chunk);
    ctx.req.on('end', () => resolve(Object.fromEntries(new URLSearchParams(body))));
  });

  const isValid = await bcrypt.compare(data.code, process.env.MASTER_HASH);
  if (isValid) {
    ctx.cookies.set('master', data.code, { httpOnly: true });
    ctx.redirect('/?admin=1');
  } else {
    ctx.body = `<p style="color:red;text-align:center;">❌ Incorrect code</p><script>setTimeout(()=>{location.href='/admin'},2000)</script>`;
  }
});

module.exports = router;
const Router = require('koa-router');
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
const bcrypt = require('bcrypt');
const router = new Router();

async function requireSubscription(ctx, next) {
  const submittedCode = ctx.headers['x-master-code'] || ctx.cookies.get('master');
  const isValid = submittedCode 
    ? await bcrypt.compare(submittedCode, process.env.MASTER_HASH)
    : false;

  if (isValid) return next();

  const tier = ctx.session?.tier || 'free';
  if (tier === 'free') return next();

  const subscription = await stripe.subscriptions.retrieve(ctx.session.subId);
  if (subscription.status !== 'active') ctx.throw(402, 'Payment Required');

  return next();
}

router.get('/check', requireSubscription, async (ctx) => {
  ctx.body = { message: "Access granted" };
});

module.exports = router;
<div id="admin-badge" style="position:fixed;top:10px;right:10px;z-index:9999;display:none;">
  <span style="padding:5px 10px;background:linear-gradient(90deg,#0f0,#4caf50);color:white;
  border-radius:5px;font-weight:bold;box-shadow:0 0 8px #0f0;animation: pulse 1.5s infinite;">
    ADMIN MODE
    <button onclick="logoutAdmin()" style="margin-left:10px;background:black;color:#0f0;
    border:none;padding:2px 6px;border-radius:4px;cursor:pointer;font-size:10px;">
      Logout
    </button>
  </span>
</div>

<script>
function logoutAdmin() {
  document.cookie = "master=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
  location.reload();
}
if (document.cookie.includes("master=")) {
  document.getElementById("admin-badge").style.display = "block";
}
</script>
const axios = require('axios');
const OpenAI = require('openai');
const shopifyAPI = require('shopify-api-node');

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const shopify = new shopifyAPI({
  shopName: process.env.SHOPIFY_SHOP_NAME,
  apiKey: process.env.SHOPIFY_API_KEY,
  password: process.env.SHOPIFY_API_PASSWORD,
});

async function fetchCJProducts() {
  const { data } = await axios.get('https://developers.cjdropshipping.com/api/product/list', {
    headers: { 'CJ-Access-Token': process.env.CJ_API_KEY }
  });
  return data.products || [];
}

async function categorizeProduct(title, description) {
  const prompt = `Categorize the following product and return JSON like {category: "", subcategory: "", tags: []}. Title: ${title}, Description: ${description}`;
  const completion = await openai.chat.completions.create({
    model: "gpt-4",
    messages: [{ role: "user", content: prompt }]
  });
  return JSON.parse(completion.choices[0].message.content);
}

async function syncProducts() {
  const products = await fetchCJProducts();

  for (const product of products) {
    const aiData = await categorizeProduct(product.name, product.description);

    await shopify.product.create({
      title: product.name,
      body_html: product.description,
      product_type: aiData.category,
      tags: aiData.tags.join(', '),
      variants: [
        {
          price: product.price,
          sku: product.sku,
          inventory_quantity: 999
        }
      ],
      images: product.images.map(img => ({ src: img }))
    });

    console.log(`✅ Synced: ${product.name}`);
  }
}

module.exports = { syncProducts };
const OpenAI = require('openai');
const { GraphAPI, TikTokAPI, PinterestAPI } = require('./platformClients'); // You build wrappers
const scheduler = require('node-cron');

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

async function generateSocialPost(product) {
  const prompt = `Create a viral social media post with SEO and AEO keywords for this product: "${product.title}" - Description: ${product.body_html}. Return JSON with {caption, hashtags, languages: [translations...]}`;
  const completion = await openai.chat.completions.create({
    model: "gpt-4",
    messages: [{ role: "user", content: prompt }]
  });
  return JSON.parse(completion.choices[0].message.content);
}

async function fetchProducts() {
  // Fetch 3 random published Shopify products
  const products = await axios.get(`https://${process.env.SHOPIFY_SHOP_NAME}.myshopify.com/admin/api/2023-10/products.json`, {
    headers: {
      "X-Shopify-Access-Token": process.env.SHOPIFY_ADMIN_TOKEN
    }
  });
  return products.data.products.sort(() => 0.5 - Math.random()).slice(0, 3);
}

async function postToAllPlatforms() {
  const products = await fetchProducts();

  for (const product of products) {
    const content = await generateSocialPost(product);

    await Promise.all([
      GraphAPI.postToFacebook(content.caption, product.image.src),
      GraphAPI.postToInstagram(content.caption, product.image.src),
      TikTokAPI.uploadVideo(product.video_url, content.caption),
      PinterestAPI.createPin(product.image.src, content.caption),
      // Extend to Reddit, Threads, Discord, X, YouTube Shorts, LinkedIn...
    ]);

    console.log(`🚀 Posted for: ${product.title}`);
  }
}

scheduler.schedule('*/144 */1 * * *', postToAllPlatforms); // 10x a day
OPENAI_API_KEY=your_openai_key_here
CJ_API_KEY=your_cj_token_here
SHOPIFY_ADMIN_TOKEN=your_private_admin_token
SHOPIFY_SHOP_NAME=shopatonestop
SHOPIFY_API_KEY=your_public_key
SHOPIFY_API_PASSWORD=your_private_app_password
const fs = require('fs');
const path = require('path');
const axios = require('axios');

const FEED_PATH = path.join(__dirname, '../public/feeds');

async function generateProductFeeds() {
  const { data } = await axios.get(`https://${process.env.SHOPIFY_SHOP_NAME}.myshopify.com/admin/api/2023-10/products.json`, {
    headers: { "X-Shopify-Access-Token": process.env.SHOPIFY_ADMIN_TOKEN }
  });

  const feedXml = data.products.map(product => `
    <item>
      <title>${product.title}</title>
      <link>https://${process.env.SHOPIFY_SHOP_NAME}.store/products/${product.handle}</link>
      <description>${product.body_html}</description>
      <g:price>${product.variants[0].price} USD</g:price>
      <g:image_link>${product.image.src}</g:image_link>
      <g:brand>${product.vendor}</g:brand>
      <g:availability>in stock</g:availability>
      <g:condition>new</g:condition>
      <g:mpn>${product.variants[0].sku}</g:mpn>
    </item>`).join('');

  const fullFeed = `<?xml version="1.0" encoding="UTF-8" ?>
  <rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
    <channel>
      <title>ShopAtOneStop Product Feed</title>
      <link>https://${process.env.SHOPIFY_SHOP_NAME}.store</link>
      <description>Automated product feed</description>
      ${feedXml}
    </channel>
  </rss>`;

  fs.writeFileSync(`${FEED_PATH}/google.xml`, fullFeed);
  fs.writeFileSync(`${FEED_PATH}/bing.xml`, fullFeed);
  fs.writeFileSync(`${FEED_PATH}/facebook.xml`, fullFeed);

  console.log("✅ Feeds generated: Google, Bing, Meta");
}

module.exports = { generateProductFeeds };
const cron = require('node-cron');
const fs = require('fs');
const axios = require('axios');
const { syncProducts } = require('./productSync');

const snapshotPath = './cache/lastProductIDs.json';

async function detectNewShopifyProducts() {
  const { data } = await axios.get(`https://${process.env.SHOPIFY_SHOP_NAME}.myshopify.com/admin/api/2023-10/products.json`, {
    headers: { "X-Shopify-Access-Token": process.env.SHOPIFY_ADMIN_TOKEN }
  });

  const newIDs = data.products.map(p => p.id);
  const previous = fs.existsSync(snapshotPath)
    ? JSON.parse(fs.readFileSync(snapshotPath))
    : [];

  const diff = newIDs.filter(id => !previous.includes(id));
  if (diff.length > 0) {
    console.log("🚨 New product(s) detected! Syncing feeds + AI posts...");
    await syncProducts(); // Refresh Shopify with latest categorization
    require('./feedGenerator').generateProductFeeds();
    require('./aiSwarmPoster').postToAllPlatforms();
  }

  fs.writeFileSync(snapshotPath, JSON.stringify(newIDs));
}

cron.schedule('*/10 * * * *', detectNewShopifyProducts); // every 10 minutes
const axios = require('axios');

const GraphAPI = {
  async postToFacebook(caption, image) {
    await axios.post(`https://graph.facebook.com/v18.0/${process.env.FB_PAGE_ID}/photos`, {
      url: image,
      caption,
      access_token: process.env.FB_ACCESS_TOKEN
    });
  },
  async postToInstagram(caption, image) {
    const { data } = await axios.post(`https://graph.facebook.com/v18.0/${process.env.IG_USER_ID}/media`, {
      image_url: image,
      caption,
      access_token: process.env.FB_ACCESS_TOKEN
    });
    await axios.post(`https://graph.facebook.com/v18.0/${process.env.IG_USER_ID}/media_publish`, {
      creation_id: data.id,
      access_token: process.env.FB_ACCESS_TOKEN
    });
  }
};

const TikTokAPI = {
  async uploadVideo(videoUrl, caption) {
    // Placeholder for TikTok upload via API (limited access, require Business app approval)
    console.log("TikTok upload simulated:", caption, videoUrl);
  }
};

module.exports = { GraphAPI, TikTokAPI };
FB_PAGE_ID=your_facebook_page_id
FB_ACCESS_TOKEN=your_facebook_graph_token
IG_USER_ID=your_instagram_user_id
const axios = require('axios');

async function loadFromSpocket() {
  const { data } = await axios.get('https://api.spocket.co/v1/products', {
    headers: { Authorization: `Bearer ${process.env.SPOCKET_API_KEY}` }
  });
  return data.products;
}

async function loadFromSyncee() {
  const { data } = await axios.get('https://api.syncee.co/products', {
    headers: { Authorization: `Bearer ${process.env.SYNCEE_API_KEY}` }
  });
  return data.products;
}

async function loadFromPrintful() {
  const { data } = await axios.get('https://api.printful.com/products', {
    headers: { Authorization: `Bearer ${process.env.PRINTFUL_API_KEY}` }
  });
  return data.result;
}

async function loadAllSuppliers() {
  const [spocket, syncee, printful] = await Promise.all([
    loadFromSpocket(),
    loadFromSyncee(),
    loadFromPrintful()
  ]);

  return [...spocket, ...syncee, ...printful];
}

module.exports = { loadAllSuppliers };
SPOCKET_API_KEY=your_spocket_key
SYNCEE_API_KEY=your_syncee_key
PRINTFUL_API_KEY=your_printful_key
require('dotenv').config();
const express = require('express');
const cron = require('node-cron');
const { syncProducts } = require('./services/productSync');
const { generateProductFeeds } = require('./services/feedGenerator');
const { postToAllPlatforms } = require('./services/aiSwarmPoster');
const { detectNewShopifyProducts } = require('./services/triggerWatcher');
const { loadAllSuppliers } = require('./services/supplierLoader');

const app = express();
const PORT = process.env.PORT || 5000;

app.get("/", (req, res) => {
  res.send("✅ Shopatonestop automation engine running.");
});

// 🧠 Manual Sync Endpoint
app.get("/sync-now", async (req, res) => {
  await syncProducts();
  await generateProductFeeds();
  await postToAllPlatforms();
  res.send("✅ Full sync + feed + post completed.");
});

// 🧬 Supplier Pull Endpoint
app.get("/load-suppliers", async (req, res) => {
  const all = await loadAllSuppliers();
  res.send(`✅ Loaded ${all.length} products from external suppliers.`);
});

// 🎯 Product Watcher Trigger
cron.schedule('*/10 * * * *', detectNewShopifyProducts); // every 10 mins

// 📡 Feed Refresh
cron.schedule('0 */6 * * *', generateProductFeeds); // every 6 hours

// 🤖 Daily Swarm Post Blitz
cron.schedule('*/144 */1 * * *', postToAllPlatforms); // 10/day

app.listen(PORT, () => {
  console.log(`🚀 Jarvis: Fully armed at http://localhost:${PORT}`);
});
/project-root
│
├── main.js
├── .env
├── server.js
├── /routes
│   ├── admin.js
│   └── billing.js
│
├── /services
│   ├── productSync.js
│   ├── aiSwarmPoster.js
│   ├── feedGenerator.js
│   ├── triggerWatcher.js
│   └── supplierLoader.js
│
├── /platformClients
│   └── index.js
│
├── /cache
│   └── lastProductIDs.json
│
└── /public
    └── /feeds
        ├── google.xml
        ├── bing.xml
        └── facebook.xml
      npm install koa koa-router koa-bodyparser dotenv bcrypt stripe openai axios express node-cron shopify-api-node
node main.js
1 0 * * * cd /path/to/your/project && /usr/bin/node main.js >> /var/log/shopatonestop.log 2>&1
name = "The Complete Dropshipping Automation App"
version = "1"
app_url = "https://yourdomain.com"
embedded = true

[oauth]
scopes = "read_products, write_products, read_orders, write_orders, read_script_tags, write_script_tags"

[ui]
primary = true
<!DOCTYPE html>
<html>
<head>
  <title>App</title>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <script src="https://unpkg.com/@shopify/app-bridge"></script>
</head>
<body style="margin:0;padding:0;">
  <iframe src="https://yourdomain.com/dashboard" width="100%" height="100%" frameborder="0"></iframe>
</body>
</html>
render.yaml
services:
  - type: web
    name: title 
    env: node
    buildCommand: npm install
    startCommand: node main.js
   const Router = require('koa-router');
const router = new Router();

router.post('/init', async (ctx) => {
  const {
    shopifyStoreName,
    shopifyAdminToken,
    cjApiKey,
    openaiApiKey,
    fbAccessToken,
    stripeApiKey,
  } = ctx.request.body;

  // ⚠️ Save securely - this is where you'd insert DB encryption or secure env storage
  const session = {
    shop: shopifyStoreName,
    token: shopifyAdminToken,
    cj: cjApiKey,
    ai: openaiApiKey,
    fb: fbAccessToken,
    stripe: stripeApiKey
  };

  ctx.session.userSession = session;
  ctx.body = { success: true, message: "Session initialized." };
});
async function syncProducts(session) {
  const shopify = new ShopifyAPI({
    shopName: session.shop,
    password: session.token,
    apiKey: process.env.SHOPIFY_API_KEY // still static for app authentication
  });

  const { data } = await axios.get(`https://${session.shop}.myshopify.com/admin/api/2023-10/products.json`, {
    headers: { "X-Shopify-Access-Token": session.token }
  });

  // Continue using session variables like session.cj, session.ai, etc.
}
app.get("/sync-now", async (req, res) => {
  const session = req.session.userSession;
  if (!session) return res.status(403).send("⛔ No session found.");

  await syncProducts(session);
  await generateProductFeeds(session);
  await postToAllPlatforms(session);
  res.send("✅ Synced with your Shopify store.");
});
<form id="connectForm" method="POST" action="/init">
  <input type="text" name="shopifyStoreName" placeholder="yourstore.myshopify.com" required />
  <input type="text" name="shopifyAdminToken" placeholder="Shopify Admin API Token" required />
  <input type="text" name="cjApiKey" placeholder="CJ Dropshipping API Key" />
  <input type="text" name="openaiApiKey" placeholder="OpenAI API Key" />
  <input type="text" name="stripeApiKey" placeholder="Stripe Secret Key" />
  <input type="text" name="fbAccessToken" placeholder="Facebook Token" />
  <button type="submit">Connect Store</button>
</form>
if (session.masterKey === process.env.MASTER_OVERRIDE_KEY) {
  // Unlimited access, no rate limits, no billing
}
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  shopify_store TEXT UNIQUE NOT NULL,
  shopify_token TEXT NOT NULL,
  cj_key TEXT,
  openai_key TEXT,
  fb_token TEXT,
  stripe_key TEXT,
  is_admin BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
npm install pg
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL, // Add this to .env
  ssl: { rejectUnauthorized: false } // If using Supabase or remote PG
});

module.exports = {
  query: (text, params) => pool.query(text, params)
};
const Router = require('koa-router');
const db = require('../db');
const router = new Router();

router.post('/init', async (ctx) => {
  const {
    email,
    shopifyStore,
    shopifyToken,
    cjKey,
    openaiKey,
    fbToken,
    stripeKey
  } = ctx.request.body;

  const existing = await db.query('SELECT * FROM users WHERE shopify_store = $1', [shopifyStore]);
  if (existing.rows.length > 0) {
    return ctx.body = { success: false, message: 'Store already registered.' };
  }

  await db.query(`
    INSERT INTO users (email, shopify_store, shopify_token, cj_key, openai_key, fb_token, stripe_key)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
  `, [email, shopifyStore, shopifyToken, cjKey, openaiKey, fbToken, stripeKey]);

  ctx.body = { success: true, message: "✅ Store connected." };
});
const Router = require('koa-router');
const db = require('../db');
const router = new Router();

router.get('/all-users', async (ctx) => {
  const master = ctx.headers['x-master-key'];
  if (master !== process.env.MASTER_OVERRIDE_KEY) {
    return ctx.status = 403, ctx.body = { error: 'Forbidden' };
  }

  const result = await db.query('SELECT id, email, shopify_store, created_at FROM users ORDER BY created_at DESC');
  ctx.body = result.rows;
});
npm install stripe
const Router = require('koa-router');
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
const db = require('../db');
const router = new Router();

router.post('/create-checkout-session', async (ctx) => {
  const { email, store } = ctx.request.body;

  const session = await stripe.checkout.sessions.create({
    payment_method_types: ['card'],
    line_items: [{
      price: process.env.STRIPE_PRICE_ID, // Set this up in Stripe
      quantity: 1
    }],
    mode: 'subscription',
    customer_email: email,
    success_url: `https://yourdomain.com/success?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `https://yourdomain.com/cancel`
  });

  await db.query(`UPDATE users SET stripe_key = $1 WHERE shopify_store = $2`, [session.id, store]);
  ctx.body = { url: session.url };
});

router.post('/cancel-subscription', async (ctx) => {
  const { subscriptionId } = ctx.request.body;

  await stripe.subscriptions.update(subscriptionId, { cancel_at_period_end: true });
  ctx.body = { message: '🚫 Subscription cancellation scheduled.' };
});
DATABASE_URL=postgres://your-db-url
STRIPE_SECRET_KEY=sk_live_*********
STRIPE_PRICE_ID=price_**********
MASTER_OVERRIDE_KEY=YOUR_MASTER_KEY
#!/bin/bash

echo "🧹 Sanitizing code: Redacting private store identifiers..."

STORE_NAME="shopatonestop"
DOMAIN_NAME="shopatonestop.store"

FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(js|jsx|ts|html|env|json)$')

for FILE in $FILES; do
  if grep -q "$STORE_NAME" "$FILE"; then
    echo "⛔ Found hardcoded store name in $FILE"
    sed -i "s/$STORE_NAME/YOUR_SHOPIFY_STORE/g" "$FILE"
  fi
  if grep -q "$DOMAIN_NAME" "$FILE"; then
    echo "⛔ Found domain in $FILE"
    sed -i "s/$DOMAIN_NAME/YOUR_DOMAIN/g" "$FILE"
  fi
  git add "$FILE"
done

echo "✅ Redaction complete. Proceeding with commit."
import { useEffect, useState } from 'react';
import axios from 'axios';

function App() {
  const [users, setUsers] = useState([]);

  useEffect(() => {
    axios.get('/admin/all-users', {
      headers: { 'x-master-key': process.env.REACT_APP_ADMIN_KEY }
    }).then(res => setUsers(res.data));
  }, []);

  return (
    <div className="p-8 bg-gray-100 min-h-screen">
      <h1 className="text-3xl font-bold mb-6">🚀 Admin Dashboard</h1>
      <table className="w-full bg-white shadow rounded">
        <thead>
          <tr>
            <th>Email</th>
            <th>Shop</th>
            <th>Date</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map(u => (
            <tr key={u.id}>
              <td>{u.email}</td>
              <td>{u.shopify_store}</td>
              <td>{new Date(u.created_at).toLocaleString()}</td>
              <td><button className="bg-red-500 text-white px-2 py-1 rounded">Delete</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;
npm run build
# Serve with nginx or Vercel
npm install nodemailer
const nodemailer = require("nodemailer");

const transporter = nodemailer.createTransport({
  service: "gmail", // or SMTP of your provider
  auth: {
    user: process.env.NOTIFY_EMAIL,
    pass: process.env.NOTIFY_PASS
  }
});

function sendSignupEmail(email, store) {
  return transporter.sendMail({
    from: '"ShopAtOneStop Alerts" <no-reply@yourdomain.com>',
    to: process.env.ADMIN_EMAIL,
    subject: "🆕 New Store Connected",
    text: `Store: ${store}\nEmail: ${email}`
  });
}

function sendBillingFailure(email, reason) {
  return transporter.sendMail({
    from: '"ShopAtOneStop Billing" <billing@yourdomain.com>',
    to: process.env.ADMIN_EMAIL,
    subject: "⚠️ Stripe Billing Failed",
    text: `Failure for ${email}:\n${reason}`
  });
}

module.exports = { sendSignupEmail, sendBillingFailure };
await stripe.customers.update(customer.id, {
  name: "ShopAtOneStop",
  email: email,
  address: { country: "NZ" }
});
REACT_APP_ADMIN_KEY=your_master_key
NOTIFY_EMAIL=your_notify_email@gmail.com
NOTIFY_PASS=your_app_password
ADMIN_EMAIL=you@yourdomain.com
npm install posthog-node
const { PostHog } = require("posthog-node");
const posthog = new PostHog(process.env.POSTHOG_API_KEY, {
  host: 'https://app.posthog.com'
});

function trackSignup(email, store) {
  posthog.capture({
    distinctId: email,
    event: 'user_signed_up',
    properties: { store }
  });
}

function trackSubscriptionCancel(email) {
  posthog.capture({
    distinctId: email,
    event: 'subscription_cancelled'
  });
}

function trackLogin(email) {
  posthog.capture({
    distinctId: email,
    event: 'user_logged_in'
  });
}

module.exports = { trackSignup, trackSubscriptionCancel, trackLogin };
const Router = require('koa-router');
const db = require('../db');
const router = new Router();
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);

router.post('/webhook', async (ctx) => {
  const sig = ctx.request.headers['stripe-signature'];

  let event;
  try {
    event = stripe.webhooks.constructEvent(ctx.req.rawBody, sig, process.env.STRIPE_WEBHOOK_SECRET);
  } catch (err) {
    ctx.status = 400;
    ctx.body = `Webhook Error: ${err.message}`;
    return;
  }

  const email = event.data.object.customer_email || 'unknown';

  switch (event.type) {
    case 'invoice.payment_failed':
      await db.query('UPDATE users SET is_suspended = true WHERE email = $1', [email]);
      notifyDiscord(`⚠️ Subscription FAILED for: ${email}`);
      break;

    case 'invoice.payment_succeeded':
      await db.query('UPDATE users SET is_suspended = false WHERE email = $1', [email]);
      notifyDiscord(`✅ Subscription RESUMED for: ${email}`);
      break;
  }

  ctx.status = 200;
});
router.use(async (ctx, next) => {
  const session = ctx.session.userSession;
  const res = await db.query('SELECT is_suspended FROM users WHERE shopify_store = $1', [session.shop]);
  if (res.rows[0].is_suspended) {
    ctx.status = 403;
    ctx.body = { error: '🔒 Subscription inactive. Please update billing.' };
    return;
  }
  await next();
});
const axios = require('axios');

const WEBHOOK_URL = process.env.DISCORD_WEBHOOK_URL;

function notifyDiscord(message) {
  return axios.post(WEBHOOK_URL, {
    content: message
  });
}

module.exports = { notifyDiscord };
POSTHOG_API_KEY=phc_your_key
STRIPE_WEBHOOK_SECRET=whsec_***
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/****
import { useEffect, useState } from 'react';
import Chart from 'chart.js/auto';
import axios from 'axios';

function Dashboard() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    axios.get('/admin/metrics', {
      headers: { 'x-master-key': process.env.REACT_APP_ADMIN_KEY }
    }).then(res => setStats(res.data));
  }, []);

  useEffect(() => {
    if (!stats) return;

    const ctx = document.getElementById('userChart').getContext('2d');
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: stats.dates,
        datasets: [{
          label: 'New Users',
          data: stats.userCounts,
          borderColor: '#4F46E5',
          fill: false
        }]
      }
    });

    const ctx2 = document.getElementById('revenueChart').getContext('2d');
    new Chart(ctx2, {
      type: 'bar',
      data: {
        labels: stats.dates,
        datasets: [{
          label: 'Revenue (USD)',
          data: stats.revenue,
          backgroundColor: '#10B981'
        }]
      }
    });
  }, [stats]);

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">📊 Analytics Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <canvas id="userChart" width="400" height="200"></canvas>
        <canvas id="revenueChart" width="400" height="200"></canvas>
      </div>
    </div>
  );
}

export default Dashboard;
router.get('/metrics', async (ctx) => {
  const master = ctx.headers['x-master-key'];
  if (master !== process.env.MASTER_OVERRIDE_KEY) return ctx.status = 403;

  const users = await db.query(`
    SELECT DATE(created_at) AS date, COUNT(*) AS count
    FROM users
    GROUP BY date
    ORDER BY date DESC LIMIT 14
  `);

  const revenue = await db.query(`
    SELECT DATE(created_at) AS date, SUM(amount) AS total
    FROM stripe_transactions
    GROUP BY date
    ORDER BY date DESC LIMIT 14
  `);

  ctx.body = {
    dates: users.rows.map(r => r.date),
    userCounts: users.rows.map(r => r.count),
    revenue: revenue.rows.map(r => parseFloat(r.total || 0).toFixed(2))
  };
});
npm install node-cron
const cron = require('node-cron');
const db = require('./db');
const { notifyDiscord } = require('./services/discord');

cron.schedule('0 4 * * *', async () => {
  const unpaid = await db.query(`
    SELECT email FROM users
    WHERE is_suspended = false AND NOT EXISTS (
      SELECT 1 FROM stripe_transactions WHERE stripe_transactions.user_email = users.email
      AND created_at > now() - interval '30 days'
    )
  `);

  for (let user of unpaid.rows) {
    await db.query('UPDATE users SET is_suspended = true WHERE email = $1', [user.email]);
    await notifyDiscord(`🔒 Daily suspension: ${user.email}`);
  }

  console.log(`✅ Cron ran: ${unpaid.rows.length} accounts suspended.`);
});
npm install twilio
const twilio = require('twilio');
const client = twilio(process.env.TWILIO_SID, process.env.TWILIO_TOKEN);

const vipEmails = ['vip1@example.com', 'vip2@example.com'];

function sendVIPChurnAlert(email) {
  if (!vipEmails.includes(email)) return;

  return client.messages.create({
    to: process.env.ADMIN_PHONE,
    from: process.env.TWILIO_PHONE,
    body: `⚠️ ALERT: VIP ${email} cancelled or failed payment.`
  });
}

module.exports = { sendVIPChurnAlert };
case 'customer.subscription.deleted':
case 'invoice.payment_failed':
  await sendVIPChurnAlert(email);
  break;
REACT_APP_ADMIN_KEY=your_master_key
TWILIO_SID=ACxxxxxxxxxxxxxxxx
TWILIO_TOKEN=xxxxxxxxxxxxxxxx
TWILIO_PHONE=+12223334444
ADMIN_PHONE=+64211234567
ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'viewer';
function requireRole(role) {
  return async (ctx, next) => {
    const session = ctx.session.userSession;
    const res = await db.query('SELECT role FROM users WHERE email = $1', [session.email]);
    if (!res.rows.length || res.rows[0].role !== role) {
      ctx.status = 403;
      ctx.body = { error: '❌ Access Denied' };
      return;
    }
    await next();
  };
}
router.post('/admin/delete-user', requireRole('admin'), async (ctx) => {
  // Only admins can delete
});
router.post('/send-receipt', requireRole('admin'), async (ctx) => {
  const { customerId, invoiceId } = ctx.request.body;
  const invoice = await stripe.invoices.retrieve(invoiceId, { expand: ['customer'] });

  await stripe.invoices.sendInvoice(invoice.id);
  ctx.body = { message: '🧾 Receipt sent to ' + invoice.customer.email };
});
function calculateHealth(user) {
  let score = 100;

  if (!user.last_login || new Date(user.last_login) < Date.now() - 14 * 86400000) score -= 20;
  if (user.posts_published === 0) score -= 20;
  if (user.failed_payments > 0) score -= 30;
  if (user.support_tickets > 2) score -= 10;

  return Math.max(0, score); // range 0–100
}
cron.schedule('0 6 * * *', async () => {
  const users = await db.query('SELECT * FROM users');

  for (let user of users.rows) {
    const score = calculateHealth(user);
    if (score < 50) {
      notifyDiscord(`🚨 Low Health Score: ${user.email} = ${score}`);
      sendLowScoreEmail(user.email, score);
    }
  }
});
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import './styles.css';

function AdminPanel() {
  const [users, setUsers] = useState([]);

  useEffect(() => {
    fetchUsers();
    const interval = setInterval(fetchUsers, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchUsers = async () => {
    const res = await axios.get('/admin/users', {
      headers: { 'x-master-key': process.env.REACT_APP_ADMIN_KEY }
    });
    setUsers(res.data);
  };

  const colorCode = (score) => {
    if (score >= 90) return 'green';
    if (score >= 70) return 'yellow';
    if (score >= 40) return 'orange';
    return 'red';
  };

  return (
    <div className="p-8 bg-gray-100 min-h-screen">
      <h1 className="text-4xl font-bold mb-4">🧠 Admin Command Console</h1>
      <table className="table-auto w-full bg-white shadow-xl rounded-lg overflow-hidden">
        <thead>
          <tr className="bg-gray-200 text-left">
            <th className="p-3">Email</th>
            <th>Role</th>
            <th>Store</th>
            <th>Status</th>
            <th>Health</th>
            <th>Joined</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map(u => (
            <tr key={u.id} className="border-b hover:bg-gray-50 transition">
              <td className="p-3">{u.email}</td>
              <td>{u.role}</td>
              <td>{u.shopify_store}</td>
              <td>
                {u.is_suspended ? '🔒 Suspended' : '✅ Active'}
              </td>
              <td className={`font-bold text-${colorCode(u.health_score)}-500`}>
                {u.health_score}
              </td>
              <td>{new Date(u.created_at).toLocaleDateString()}</td>
              <td className="space-x-2">
                <button className="bg-blue-500 text-white px-2 py-1 rounded">Upgrade</button>
                <button className="bg-yellow-500 text-white px-2 py-1 rounded">Suspend</button>
                <button className="bg-red-600 text-white px-2 py-1 rounded">Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default AdminPanel;
router.get('/admin/users', async (ctx) => {
  const key = ctx.headers['x-master-key'];
  if (key !== process.env.MASTER_OVERRIDE_KEY) return ctx.status = 403;

  const res = await db.query(`
    SELECT id, email, shopify_store, role, is_suspended, created_at,
           last_login, posts_published, failed_payments, support_tickets
    FROM users
  `);

  const enhanced = res.rows.map(u => ({
    ...u,
    health_score: calculateHealth(u)
  }));

  ctx.body = enhanced;
});
.text-green-500 { color: #10B981; }
.text-yellow-500 { color: #F59E0B; }
.text-orange-500 { color: #F97316; }
.text-red-500 { color: #EF4444; }
POST /admin/suspend-user
POST /admin/promote-user
POST /admin/delete-user
requireRole('admin')
<a
  href={`https://app.posthog.com/person/${u.email}`}
  target="_blank"
  rel="noreferrer"
  className="text-sm text-blue-700 underline ml-2"
>
  Session
</a>
const adminSessions = new Set();

router.post('/admin/login', async (ctx) => {
  const { code } = ctx.request.body;
  if (code !== process.env.MASTER_OVERRIDE_KEY) {
    ctx.status = 403;
    ctx.body = { error: '❌ Invalid Code' };
    return;
  }
  adminSessions.add(ctx.sessionID);
  ctx.body = { success: true };
});

function requireMaster(ctx, next) {
  if (!adminSessions.has(ctx.sessionID)) {
    ctx.status = 403;
    ctx.body = { error: '🔒 Admin session not authorized' };
    return;
  }
  return next();
}
CREATE TABLE admin_logs (
  id SERIAL PRIMARY KEY,
  email TEXT,
  action TEXT,
  timestamp TIMESTAMP DEFAULT NOW()
);
await db.query(
  'INSERT INTO admin_logs (email, action) VALUES ($1, $2)',
  [ctx.session.email, 'Suspended user X']
);
router.get('/admin/analytics', requireRole('admin'), async (ctx) => {
  const [activeSubs, totalSubs, revenue, cancels, invoices] = await Promise.all([
    db.query(`SELECT COUNT(*) FROM stripe_subs WHERE status = 'active'`),
    db.query(`SELECT COUNT(*) FROM users WHERE role != 'viewer'`),
    db.query(`SELECT SUM(amount) FROM stripe_subs WHERE status = 'active'`),
    db.query(`SELECT COUNT(*) FROM stripe_events WHERE type = 'customer.subscription.deleted' AND created_at > now() - interval '30 days'`),
    db.query(`SELECT user_email, SUM(amount) as total, MAX(created_at) as latest FROM stripe_invoices GROUP BY user_email`)
  ]);

  const churnRate = (parseInt(cancels.rows[0].count) / parseInt(activeSubs.rows[0].count)) * 100 || 0;
  const avgLTV = invoices.rows.reduce((acc, u) => acc + parseFloat(u.total), 0) / invoices.rows.length || 0;

  ctx.body = {
    totalSubscribers: totalSubs.rows[0].count,
    activeSubscriptions: activeSubs.rows[0].count,
    monthlyRevenue: parseFloat(revenue.rows[0].sum || 0),
    churnRate: churnRate.toFixed(2),
    avgLTV: avgLTV.toFixed(2)
  };
});
import React, { useEffect, useState } from 'react';
import axios from 'axios';

function AnalyticsModule() {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    axios.get('/admin/analytics', {
      headers: { 'x-master-key': process.env.REACT_APP_ADMIN_KEY }
    }).then(res => setMetrics(res.data));
  }, []);

  if (!metrics) return <p>Loading...</p>;

  return (
    <div className="p-6 bg-white rounded shadow mt-8">
      <h2 className="text-xl font-bold mb-4">📊 SubCom: Subscription Command</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
        <MetricCard label="Total Subscribers" value={metrics.totalSubscribers} color="blue" />
        <MetricCard label="Active Subscriptions" value={metrics.activeSubscriptions} color="green" />
        <MetricCard label="Monthly Revenue (USD)" value={`$${metrics.monthlyRevenue}`} color="indigo" />
        <MetricCard label="30-Day Churn Rate" value={`${metrics.churnRate}%`} color="red" />
        <MetricCard label="Avg Lifetime Value (LTV)" value={`$${metrics.avgLTV}`} color="purple" />
      </div>
    </div>
  );
}

function MetricCard({ label, value, color }) {
  return (
    <div className={`bg-${color}-100 text-${color}-900 p-4 rounded shadow-sm`}>
      <p className="text-sm uppercase">{label}</p>
      <h3 className="text-2xl font-bold">{value}</h3>
    </div>
  );
}

export default AnalyticsModule;
