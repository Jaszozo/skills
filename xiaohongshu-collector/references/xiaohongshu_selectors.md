# Xiaohongshu UI Element Selectors

Common CSS selectors and DOM patterns for Xiaohongshu (小红书) web interface.

**Note**: These selectors may change as Xiaohongshu updates their website. Use `find` tool and `read_page` to verify current selectors.

## Search Interface

### Search Bar
- **Input field**: `input[placeholder*="搜索"]` or `.search-input`
- **Search button**: `button[type="submit"]` or `.search-btn`
- **Search icon**: Element with search icon, often clickable

### Search Results
- **Results container**: `.feeds-container` or `.note-list`
- **Individual post card**: `.note-item` or `.feed-card`
- **Post thumbnail**: `img.cover` or `.note-cover`
- **Post title overlay**: `.title` or `.note-title`

## Post Detail View

### Modal/Popup Container
- **Modal wrapper**: `.note-detail-modal` or `[role="dialog"]`
- **Modal content**: `.modal-content` or `.note-detail-content`
- **Close button**: `.close-btn` or `button[aria-label="关闭"]`

### Post Content
- **Main title**: `h1.title` or `.note-title`
- **Post description**: `.note-desc` or `.desc-content`
- **Post images**: `.carousel-container img` or `.note-image`

### Author Information
- **Author avatar**: `.author-avatar img` or `.avatar-image`
- **Author name**: `.author-name` or `.username`
- **Author link**: `a.author-link`

### Engagement Metrics
- **Like count**: `.like-count` or `[data-type="like"]`
- **Like button**: `.like-btn` or `button.interact-btn[title*="赞"]`
- **Comment count**: `.comment-count`
- **Collect/Save count**: `.collect-count`

Common patterns:
```javascript
// Like count often in format like:
<span class="count">1.2万</span>
// Or with data attribute:
<div data-like-count="12000">1.2万</div>
```

## Login Interface

### Login Indicators
- **Logged out state**: 
  - `button:contains("登录")` 
  - `.login-btn`
  - Absence of user avatar
- **Logged in state**:
  - `.user-avatar` present
  - `.user-menu` or `.profile-dropdown`
  - Presence of user icon in top right

### Login Modal
- **QR Code container**: `.qr-code-container` or `.scan-login`
- **QR Code image**: `img.qr-code`
- **Phone login tab**: `[data-tab="phone"]` or button containing "手机登录"
- **Email login tab**: `[data-tab="email"]`

## Filtering and Sorting

### Sort Options
- **Sort dropdown**: `.sort-select` or `select[name="sort"]`
- **Sort by latest**: `option[value="time"]` or button containing "最新"
- **Sort by popular**: `option[value="popular"]` or button containing "最热"

### Filter Options
- **Filter panel**: `.filter-panel` or `.sidebar-filter`
- **Category filters**: `.category-item` or `[data-filter-type="category"]`

## Common Class Patterns

Xiaohongshu often uses BEM-style naming:
- `note-*` for post-related elements
- `author-*` for author-related elements  
- `interact-*` for engagement buttons
- `modal-*` for popup/overlay elements
- `feed-*` for list/feed view elements

## Dynamic Content

### Infinite Scroll
- **Load trigger**: Bottom of `.feeds-container`
- **Loading indicator**: `.loading-spinner` or text "加载中..."
- **End of results**: Text like "没有更多了" or `.no-more-data`

### Image Lazy Loading
- Images may have `data-src` instead of `src` initially
- Wait for images to load before taking screenshots

## XPath Alternatives

If CSS selectors fail, try XPath:
- **Search input**: `//input[contains(@placeholder, '搜索')]`
- **Post title**: `//h1[contains(@class, 'title')]`
- **Like count**: `//*[contains(@class, 'like-count')]`
- **Author name**: `//*[contains(@class, 'author-name')]`

## Detection Tips

When auto-detecting elements:
1. Use `find` tool with natural language queries first
2. Fall back to `read_page` to inspect DOM structure
3. Look for stable identifiers (data attributes, aria labels)
4. Avoid relying solely on class names (they may be obfuscated)
5. Check multiple selectors as fallbacks

## Recent Changes (as of 2025)

- Xiaohongshu has been using more dynamic class names (e.g., random hash suffixes)
- Modal containers may use React portals (rendered outside main app div)
- Like counts often abbreviated (万 for 10,000+)
- Some elements require user login to appear

## Recommended Approach

Instead of hardcoding selectors, use this workflow:
1. Take screenshot to identify visual target
2. Use `find` tool: "post detail modal" or "like count"
3. Use returned `ref_id` to interact with element
4. Store working patterns for session consistency
