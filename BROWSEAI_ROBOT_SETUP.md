# BrowseAI Robot Setup Guide for SoleID

## Overview
BrowseAI robots are automated web scrapers that can extract structured data from websites. For SoleID, we'll create robots to scrape sneaker images, prices, and product details from major retailers.

## Step 1: Access BrowseAI Dashboard
1. Go to [browse.ai](https://browse.ai)
2. Login with your API credentials: `c6639012-5b3b-4f11-a0c4-3e5804a82c1d:dd38b1a2-9ee9-487c-a595-dfc8bde92168`
3. Navigate to "My Robots" section

## Step 2: Create Nike Product Robot

### Robot Configuration:
- **Name**: `Nike Sneaker Scraper`
- **Type**: `Bulk List`
- **Target URL**: `https://www.nike.com/t/air-force-1-07-mens-shoes-CW2288/CW2288-111`

### Data Fields to Extract:
```json
{
  "product_name": {
    "selector": "h1[data-automation-id='product-title']",
    "attribute": "text"
  },
  "price": {
    "selector": ".product-price",
    "attribute": "text"
  },
  "images": {
    "selector": "img[data-sub-type='product']",
    "attribute": "src",
    "multiple": true
  },
  "colorway": {
    "selector": ".product-subtitle",
    "attribute": "text"
  },
  "availability": {
    "selector": "[data-automation-id='size-availability']",
    "attribute": "text"
  },
  "description": {
    "selector": ".product-description",
    "attribute": "text"
  }
}
```

### Setup Steps:
1. Click "Create New Robot"
2. Select "Bulk List" type
3. Enter the Nike product URL
4. Use the visual selector to identify elements:
   - Click on product title → Name it "product_name"
   - Click on price → Name it "price"
   - Click on main product image → Name it "images" (set to capture multiple)
   - Click on colorway/subtitle → Name it "colorway"
   - Click on size availability → Name it "availability"

## Step 3: Create StockX Robot

### Robot Configuration:
- **Name**: `StockX Sneaker Scraper`
- **Type**: `Bulk List`
- **Target URL**: `https://stockx.com/nike-air-force-1-low-white`

### Data Fields to Extract:
```json
{
  "product_name": {
    "selector": "h1.chakra-heading",
    "attribute": "text"
  },
  "current_price": {
    "selector": "[data-testid='current-price']",
    "attribute": "text"
  },
  "images": {
    "selector": "img[data-testid='product-detail-image']",
    "attribute": "src",
    "multiple": true
  },
  "brand": {
    "selector": "[data-testid='product-detail-brand']",
    "attribute": "text"
  },
  "retail_price": {
    "selector": "[data-testid='retail-price']",
    "attribute": "text"
  },
  "last_sale": {
    "selector": "[data-testid='last-sale-price']",
    "attribute": "text"
  }
}
```

## Step 4: Create GOAT Robot

### Robot Configuration:
- **Name**: `GOAT Sneaker Scraper`
- **Type**: `Bulk List`
- **Target URL**: `https://www.goat.com/sneakers/air-force-1-07-white-cw2288-111`

### Data Fields to Extract:
```json
{
  "product_name": {
    "selector": "h1.ProductDetailsHeader__title",
    "attribute": "text"
  },
  "lowest_price": {
    "selector": ".ProductPrice__price",
    "attribute": "text"
  },
  "images": {
    "selector": ".ProductMedia__image img",
    "attribute": "src",
    "multiple": true
  },
  "brand": {
    "selector": ".ProductDetailsHeader__brand",
    "attribute": "text"
  },
  "sizes_available": {
    "selector": ".SizeSelector__size",
    "attribute": "text",
    "multiple": true
  }
}
```

## Step 5: Test Robots

### Testing Process:
1. After creating each robot, click "Test Run"
2. Verify that all fields are being captured correctly
3. Check that images are high-quality product photos
4. Ensure prices are formatted correctly
5. Validate that multiple images are captured

### Expected Results:
- **Nike Robot**: Should capture 5-10 product images per sneaker
- **StockX Robot**: Should capture current market prices and 3-5 images
- **GOAT Robot**: Should capture lowest prices and 4-8 images

## Step 6: Schedule and Monitor

### Scheduling Options:
- **Manual**: Run robots on-demand via API
- **Scheduled**: Daily runs for popular products
- **Webhook**: Trigger when new products are added to database

### Monitoring:
- Check robot success rates in BrowseAI dashboard
- Monitor API usage (50 requests/day limit)
- Review extracted data quality

## Step 7: Integration with SoleID

### API Integration:
```python
# Example API call to run robot
import requests

headers = {
    "Authorization": "Bearer c6639012-5b3b-4f11-a0c4-3e5804a82c1d:dd38b1a2-9ee9-487c-a595-dfc8bde92168"
}

# Run Nike robot
response = requests.post(
    "https://api.browse.ai/v2/robots/ROBOT_ID/tasks",
    headers=headers,
    json={
        "inputParameters": {
            "originUrl": "https://www.nike.com/t/air-force-1-07-mens-shoes-CW2288/CW2288-111"
        }
    }
)
```

## Expected Benefits

### Image Collection:
- **Quality**: High-resolution product images directly from retailers
- **Quantity**: 5-10 images per sneaker from multiple angles
- **Reliability**: Consistent data structure and format

### Price Data:
- **Real-time**: Current market prices from StockX and GOAT
- **Historical**: Track price changes over time
- **Retail**: Original retail prices from Nike/Adidas

### Coverage Improvement:
- **Current**: 0.4% coverage (441/123,733 sneakers)
- **Target**: 15-20% coverage within 30 days
- **Quality**: Professional product photos vs. scraped images

## Troubleshooting

### Common Issues:
1. **Selector Changes**: Websites update their HTML structure
   - Solution: Update robot selectors monthly
2. **Rate Limiting**: Too many requests
   - Solution: Implement delays between API calls
3. **Image Quality**: Low-resolution or placeholder images
   - Solution: Add image size validation

### Fallback Strategy:
- If BrowseAI robots fail, fall back to ScrapeNinja direct scraping
- Combine multiple data sources for better coverage
- Implement retry logic with exponential backoff

## Cost Analysis

### BrowseAI Pricing:
- **Free Tier**: 50 tasks/month
- **Starter**: $49/month for 2,000 tasks
- **Professional**: $149/month for 10,000 tasks

### ROI Calculation:
- Current manual effort: ~$500/month equivalent
- BrowseAI cost: $49-149/month
- Time savings: 80-90% reduction in manual work
- Quality improvement: Professional product images

## Next Steps

1. **Immediate**: Create Nike robot for testing
2. **Week 1**: Add StockX and GOAT robots
3. **Week 2**: Integrate with existing SoleID scrapers
4. **Week 3**: Scale up to process 100+ sneakers daily
5. **Month 1**: Achieve 15%+ image coverage

## Success Metrics

- **Image Coverage**: Increase from 0.4% to 15%+
- **Image Quality**: 95%+ high-resolution product photos
- **Data Accuracy**: 98%+ correct prices and product details
- **System Reliability**: 95%+ uptime and successful scraping