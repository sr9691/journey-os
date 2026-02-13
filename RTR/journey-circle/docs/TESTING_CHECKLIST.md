# Iteration 7: Circle Visualization — Testing Checklist

**Module**: JourneyCircleRenderer  
**Date**: February 2026

---

## 1. Canvas Rendering

### 1.1 Initial Load
- [ ] Canvas element renders at 700×700 logical pixels
- [ ] Canvas is centered within its container
- [ ] Draw-in animation plays on first load (~600ms)
- [ ] No JavaScript console errors on page load

### 1.2 Empty State (No Data)
- [ ] Ghost rings shown in grey (#e0e0e0) at 35% opacity
- [ ] Center circle shown in grey
- [ ] "0 Offers" displayed in center
- [ ] Helper text "Complete Steps 5–8 to populate your Journey Circle." shown
- [ ] Labels show "PROBLEMS" and "SOLUTIONS" without counts

### 1.3 Outer Ring — Problems
- [ ] Ring appears at 280px radius with 40px width
- [ ] Ring color is #ff6b6b (red)
- [ ] Exactly 5 equal segments visible when 5 problems exist
- [ ] White divider lines between segments (2px width)
- [ ] Outer and inner edge strokes visible
- [ ] "PROBLEMS (5)" label shown above ring
- [ ] Fewer than 5 problems: empty segments shown at 25% opacity

### 1.4 Middle Ring — Solutions
- [ ] Ring appears at 200px radius with 40px width
- [ ] Ring color is #42a5f5 (blue)
- [ ] Exactly 5 segments when 5 solutions exist
- [ ] White divider lines between segments
- [ ] "SOLUTIONS (5)" label shown below ring
- [ ] Fewer than 5 solutions: empty segments at 25% opacity

### 1.5 Center Circle — Offers
- [ ] Circle at 80px radius
- [ ] Green gradient fill (#66bb6a → #81c784)
- [ ] Offer count displayed as large number (e.g., "12")
- [ ] "Offers" label below count (or "Offer" if count is 1)
- [ ] When 0 offers: grey fill, "0" count, "Offers" label

### 1.6 Nodes
- [ ] Problem nodes: 20px radius white circles on outer ring
- [ ] Solution nodes: 16px radius white circles on middle ring
- [ ] Each node shows its position number (1–5)
- [ ] Nodes centered within ring segments (at midpoint angle)
- [ ] Nodes have subtle drop shadow
- [ ] Node borders match ring color at 60% opacity
- [ ] Nodes appear after ring animation (~40% progress)

### 1.7 Primary Problem Indicator
- [ ] Primary problem node has golden ring (#ffca28) around it
- [ ] Golden ring is 3px wide, sits 4px outside node
- [ ] Only ONE node has the primary indicator

### 1.8 Connection Lines
- [ ] Dashed lines (4px dash, 4px gap) from each problem node to matched solution node
- [ ] Dashed lines from each solution node to center
- [ ] Lines drawn at 35% opacity white
- [ ] Lines appear after 50% animation progress
- [ ] Unmatched problems show very faint dotted line to center (20% opacity)

---

## 2. Data Integration

### 2.1 API Fetching
- [ ] `init()` fetches from `/journey-circles/{id}/problems`
- [ ] `init()` fetches from `/journey-circles/{id}/solutions`
- [ ] `init()` fetches from `/journey-circles/{id}/offers`
- [ ] All three requests fire in parallel (Promise.all)
- [ ] "Loading…" indicator shown while fetching
- [ ] Nonce header (`X-WP-Nonce`) included in requests

### 2.2 No circleId
- [ ] When `circleId` is 0, no API calls made
- [ ] Empty state rendered immediately

### 2.3 API Errors
- [ ] 404 response treated as empty data (no error)
- [ ] 500 response shows error message on canvas
- [ ] Network timeout shows error message
- [ ] Error text includes "Click refresh to retry."

### 2.4 `refresh()` Method
- [ ] Calling `refresh()` re-fetches data from API
- [ ] Canvas re-draws with animation
- [ ] Previous animation cancelled before new one starts
- [ ] Loading state shown during fetch

### 2.5 `setData()` Method
- [ ] Providing `{ problems, solutions, offers }` updates canvas
- [ ] No API call made when using `setData()`
- [ ] Animation plays after data set
- [ ] Partial data accepted (e.g., problems only, no solutions)

---

## 3. Responsive Behavior

### 3.1 Desktop (≥ 1024px)
- [ ] Two-column layout: main content + sidebar with canvas
- [ ] Canvas sidebar sticky at top: 48px
- [ ] Canvas card max-width 380px in sidebar

### 3.2 Tablet (768px – 1024px)
- [ ] Layout stacks to single column
- [ ] Canvas moves below main content
- [ ] Canvas max-width 500px, centered
- [ ] All elements remain readable

### 3.3 Mobile (≤ 480px)
- [ ] Canvas max-width 320px
- [ ] Toolbar action buttons hidden
- [ ] Legend items wrap if needed
- [ ] Legend font reduced to 11px
- [ ] Canvas still renders correctly at small size

### 3.4 Canvas Scaling
- [ ] Canvas `max-width: 100%` prevents overflow
- [ ] `height: auto` maintains aspect ratio
- [ ] Rings don't get clipped at any viewport size

---

## 4. Retina / HiDPI

- [ ] On Retina displays (devicePixelRatio = 2), canvas buffer is 1400×1400
- [ ] CSS display size remains 700×700
- [ ] Rendering is crisp / non-blurry on Retina
- [ ] Text on canvas is sharp (not pixelated)
- [ ] Non-Retina displays (dpr = 1) render normally at 700×700

---

## 5. Animation

- [ ] Draw-in animation lasts ~600ms
- [ ] Easing is smooth (easeOutCubic — fast start, slow finish)
- [ ] Rings expand from center outward
- [ ] Nodes fade in after rings established (~40% progress)
- [ ] Connection lines appear after nodes (~50% progress)
- [ ] Labels fade in last (~70% progress)
- [ ] No visual flicker or tearing during animation
- [ ] `requestAnimationFrame` used (no `setInterval`)

---

## 6. Toolbar Buttons

- [ ] **Refresh** button calls `renderer.refresh()`
- [ ] **Download** button calls `renderer.downloadAsImage()`
- [ ] Downloaded file is `journey-circle.png`
- [ ] Downloaded image matches canvas content
- [ ] Buttons have hover/active states

---

## 7. Legend

- [ ] Three items: Problems (red), Solutions (blue), Offers (green)
- [ ] Swatches match ring colors exactly
- [ ] Legend centered below canvas
- [ ] Responsive: wraps on narrow screens

---

## 8. Browser Compatibility

| Browser | Version | Pass/Fail | Notes |
|---------|---------|-----------|-------|
| Chrome  | Latest  | [ ] | |
| Firefox | Latest  | [ ] | |
| Safari  | Latest  | [ ] | |
| Edge    | Latest  | [ ] | |

---

## 9. Performance

| Metric | Target | Actual | Pass/Fail |
|--------|--------|--------|-----------|
| Canvas render (full draw) | < 100ms | ___ms | [ ] |
| API fetch (3 parallel) | < 500ms | ___ms | [ ] |
| Animation frame rate | 60fps | ___fps | [ ] |
| Memory (no leaks on refresh) | Stable | ___ | [ ] |

### How to measure:
- **Render time**: Add `console.time('render')` / `console.timeEnd('render')` around `_render()`
- **API fetch**: Network tab in DevTools
- **Frame rate**: Performance tab → record during animation
- **Memory**: Take heap snapshots before and after 10x `refresh()` calls

---

## 10. Edge Cases

- [ ] 0 problems, 0 solutions, 0 offers — empty state
- [ ] 1 problem, 0 solutions — partial ring with 1 filled segment
- [ ] 5 problems, 3 solutions — 5 problem nodes, 3 solution nodes, 2 empty slots
- [ ] 5 problems, 5 solutions, 0 offers — full rings, center shows "0 Offers"
- [ ] Problem positions out of order (e.g., 0,2,4,1,3) — correct placement
- [ ] Duplicate positions — handles gracefully (no overlap crash)
- [ ] Very long problem titles — no impact (titles not shown on canvas)
- [ ] `circleId` changed mid-session — `refresh()` picks up new circle
- [ ] Rapid successive `refresh()` calls — previous animation cancelled cleanly
- [ ] Page resize during animation — no rendering artifacts

---

## Test Sign-off

| Tester | Date | Result | Notes |
|--------|------|--------|-------|
| _______ | _______ | ☐ Pass / ☐ Fail | |

---

**Definition of Done for Iteration 7:**
- [ ] Canvas displays journey circle with correct ring geometry
- [ ] Outer ring has 5 red segments for problems
- [ ] Middle ring has 5 blue segments for solutions
- [ ] Center circle shows offer count in green
- [ ] Nodes numbered 1–5 on both rings
- [ ] Primary problem has gold indicator
- [ ] Connection lines drawn between matched rings
- [ ] All data comes from REST API (no mock data)
- [ ] Updates via `refresh()` when data changes
- [ ] Canvas resizes responsively
- [ ] No rendering glitches or console errors
- [ ] Code reviewed and documented
