const express = require("express");
const cors = require("cors");
const SneaksAPI = require("sneaks-api");

const app = express();
const sneaks = new SneaksAPI();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

// Promisify Sneaks-API callbacks
function getProducts(keyword, limit) {
  return new Promise((resolve, reject) => {
    sneaks.getProducts(keyword, limit, (err, products) => {
      if (err) return reject(err);
      resolve(products || []);
    });
  });
}

function getProductPrices(styleID) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      resolve(null); // timeout gracefully after 20s
    }, 20000);

    sneaks.getProductPrices(styleID, (err, product) => {
      clearTimeout(timeout);
      if (err) return reject(err);
      resolve(product);
    });
  });
}

function getMostPopular(limit) {
  return new Promise((resolve, reject) => {
    sneaks.getMostPopular(limit, (err, products) => {
      if (err) return reject(err);
      resolve(products || []);
    });
  });
}

// Map a raw Sneaks-API product to a clean response object
function mapProduct(p) {
  return {
    name: p.shoeName,
    brand: p.brand,
    colorway: p.colorway,
    description: p.description || "",
    releaseDate: p.releaseDate,
    retailPrice: p.retailPrice,
    styleID: p.styleID,
    thumbnail: p.thumbnail,
    lowestResellPrice: p.lowestResellPrice
      ? {
          stockX: p.lowestResellPrice.stockX || null,
          goat: p.lowestResellPrice.goat || null,
          flightClub: p.lowestResellPrice.flightClub || null,
          stadiumGoods: p.lowestResellPrice.stadiumGoods || null,
        }
      : null,
    resellPrices: p.resellPrices || {},
    goatPrices: p.goatPrices || {},
    resellLinks: {
      stockX: p.resellLinks ? p.resellLinks.stockX : null,
      goat: p.resellLinks ? p.resellLinks.goat : null,
      flightClub: p.resellLinks ? p.resellLinks.flightClub : null,
      stadiumGoods: p.resellLinks ? p.resellLinks.stadiumGoods : null,
    },
    images: {
      main: p.thumbnail,
      additional: p.imageLinks || [],
    },
  };
}

// Health check
app.get("/health", (req, res) => {
  res.json({ status: "ok", service: "sneaks-service", timestamp: new Date().toISOString() });
});

// Search products by keyword
app.get("/search", async (req, res) => {
  const { q, limit = 10 } = req.query;
  if (!q) {
    return res.status(400).json({ error: "Query parameter 'q' is required" });
  }

  try {
    const products = await getProducts(q, parseInt(limit));
    const results = products.map(mapProduct);
    res.json({ count: results.length, products: results });
  } catch (err) {
    console.error("Search error:", err.message);
    res.status(500).json({ error: "Search failed", detail: err.message });
  }
});

// Get full pricing for a specific product by styleID
// First searches to get base price data, then tries detailed pricing
app.get("/prices/:styleID", async (req, res) => {
  const { styleID } = req.params;

  try {
    // Step 1: Search by styleID to get base product data + lowestResellPrice
    const searchResults = await getProducts(styleID, 1);
    let baseProduct = searchResults.find((p) => p.styleID === styleID) || searchResults[0];

    // Step 2: Try to get detailed per-size pricing (may fail on some products)
    let detailedProduct = null;
    try {
      detailedProduct = await getProductPrices(styleID);
    } catch (e) {
      console.log(`Detailed pricing unavailable for ${styleID}: ${e.message}`);
    }

    // Merge: prefer detailed data but fall back to search data
    const product = detailedProduct || baseProduct;
    if (!product) {
      return res.status(404).json({ error: "Product not found" });
    }

    const result = mapProduct(product);

    // If detailed pricing was empty but search had prices, include search prices
    if (
      baseProduct &&
      baseProduct.lowestResellPrice &&
      Object.keys(result.resellPrices).length === 0
    ) {
      result.lowestResellPrice = {
        stockX: baseProduct.lowestResellPrice.stockX || null,
        goat: baseProduct.lowestResellPrice.goat || null,
        flightClub: baseProduct.lowestResellPrice.flightClub || null,
        stadiumGoods: baseProduct.lowestResellPrice.stadiumGoods || null,
      };
    }

    res.json(result);
  } catch (err) {
    console.error("Price lookup error:", err.message);
    res.status(500).json({ error: "Price lookup failed", detail: err.message });
  }
});

// Get trending/most popular products
app.get("/trending", async (req, res) => {
  const { limit = 20 } = req.query;

  try {
    const products = await getMostPopular(parseInt(limit));
    const results = products.map(mapProduct);
    res.json({ count: results.length, products: results });
  } catch (err) {
    console.error("Trending error:", err.message);
    res.status(500).json({ error: "Trending lookup failed", detail: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Sneaks service running on http://localhost:${PORT}`);
  console.log("Endpoints:");
  console.log(`  GET /health`);
  console.log(`  GET /search?q=keyword&limit=10`);
  console.log(`  GET /prices/:styleID`);
  console.log(`  GET /trending?limit=20`);
});
