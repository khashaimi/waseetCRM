# Waseet CRM — Bubble.io Build Guide
## Step-by-Step Instructions for a Non-Developer

---

## Before You Start

1. Sign up at **bubble.io** (free plan to start)
2. Create a new app — name it "waseet-crm"
3. Set language to Arabic: Settings → General → set RTL direction
4. Install these free Bubble plugins (Plugins tab):
   - **Bubble's Own Calendar** — for follow-up scheduling
   - **Air Date/Time Picker** — for date inputs
   - **Toolbox** — for custom workflows

---

## Step 1: Data Types (Your Database)

Go to **Data → Data Types** and create these types:

---

### Data Type: User (already exists — extend it)
Add these fields to the default User type:

| Field Name | Type | Notes |
|-----------|------|-------|
| full_name | text | Agent's full name |
| phone | text | WhatsApp number |
| agency | Agency | Link to their agency |
| role | text | "agent" or "admin" |
| is_active | yes/no | Default: yes |

---

### Data Type: Agency
| Field Name | Type | Notes |
|-----------|------|-------|
| name | text | Agency name in Arabic |
| cr_number | text | Commercial registration |
| subscription_plan | text | "solo", "team", "pro", "enterprise" |
| subscription_end | date | When their trial/subscription expires |
| owner | User | Agency owner |
| agents | list of User | All agents in this agency |

---

### Data Type: Contact (العميل)
| Field Name | Type | Notes |
|-----------|------|-------|
| full_name | text | Client full name |
| phone | text | WhatsApp number |
| email | text | Optional |
| source | text | "واتساب", "إيميل", "توصية", "سيتي سكيب", "أخرى" |
| status | text | "جديد", "متابعة", "مهتم", "غير مهتم", "مغلق" |
| budget_min | number | Minimum budget in SAR |
| budget_max | number | Maximum budget in SAR |
| preferred_areas | text | Preferred neighborhoods/cities |
| property_type | text | "شقة", "فيلا", "أرض", "تجاري", "مكتب" |
| notes | text | Internal notes |
| assigned_to | User | Which agent owns this contact |
| agency | Agency | Which agency |
| created_date | date | Auto-filled |
| last_contact_date | date | Last time agent talked to them |
| next_followup_date | date | When to follow up next |

---

### Data Type: Deal (الصفقة)
| Field Name | Type | Notes |
|-----------|------|-------|
| title | text | e.g. "فيلا الملقا — أحمد العمري" |
| contact | Contact | Linked client |
| property | Property | Linked property |
| stage | text | "جديد", "معاينة", "عرض سعر", "تفاوض", "مغلقة", "ملغية" |
| deal_value | number | Expected value in SAR |
| commission_pct | number | Commission percentage |
| expected_close | date | Expected closing date |
| notes | text | Deal notes |
| assigned_to | User | Responsible agent |
| agency | Agency | |
| created_date | date | |
| closed_date | date | When actually closed |
| is_won | yes/no | Closed successfully? |

---

### Data Type: Property (العقار)
| Field Name | Type | Notes |
|-----------|------|-------|
| title | text | Property name/description |
| type | text | "شقة", "فيلا", "أرض", "تجاري" |
| price | number | Asking price in SAR |
| area_sqm | number | Area in square meters |
| bedrooms | number | |
| bathrooms | number | |
| city | text | |
| neighborhood | text | |
| description | text | |
| photos | list of image | Property photos |
| status | text | "متاح", "محجوز", "مباع" |
| agency | Agency | |
| listed_by | User | |

---

### Data Type: Activity (سجل النشاط)
| Field Name | Type | Notes |
|-----------|------|-------|
| type | text | "مكالمة", "واتساب", "بريد إلكتروني", "معاينة", "ملاحظة" |
| description | text | What happened |
| contact | Contact | Related client |
| deal | Deal | Related deal (optional) |
| done_by | User | Which agent |
| date | date | When it happened |

---

### Data Type: FollowUp (التذكير)
| Field Name | Type | Notes |
|-----------|------|-------|
| contact | Contact | Who to follow up with |
| deal | Deal | Related deal (optional) |
| due_date | date | When the reminder is due |
| note | text | What to do |
| assigned_to | User | |
| is_done | yes/no | Default: no |

---

## Step 2: Pages to Create

Go to **Design** tab and create these pages:

| Page Name | URL | Purpose |
|-----------|-----|---------|
| index | / | Landing page (or redirect to dashboard) |
| login | /login | Login / Signup |
| dashboard | /dashboard | Main overview |
| contacts | /contacts | List of all clients |
| contact-detail | /contact/:id | Single client profile |
| deals | /deals | Kanban pipeline board |
| deal-detail | /deal/:id | Single deal view |
| properties | /properties | Property listings |
| team | /team | Manage agents (admin only) |
| settings | /settings | Account/billing settings |
| onboarding | /onboarding | New user setup wizard |

---

## Step 3: Page by Page — What to Build

---

### Page: Dashboard (/dashboard)

**Layout (top to bottom):**

1. **Header strip** — Logo + user name + logout button
2. **Stats row (4 cards):**
   - Total active contacts
   - Open deals
   - Deals closed this month
   - Revenue this month (sum of closed deal values × commission)
3. **Two columns:**
   - Left (60%): Recent deals — list of last 10 deals with stage badge
   - Right (40%): Today's follow-ups — list where due_date = today and is_done = no
4. **Quick-add button** — Floating "+ عميل جديد" button

**Key Bubble workflows:**
- On page load: check User's agency subscription_end. If expired → redirect to /settings
- Stats: use "Do a search for" with count/sum aggregations

---

### Page: Contacts (/contacts)

**Layout:**
1. Search bar (search by name or phone)
2. Filter row: Status dropdown, Source dropdown, Assigned agent dropdown
3. Contact cards in a Repeating Group (grid layout, 3 columns on desktop)
4. Each card shows: Name, Phone, Status badge, Last contact date, Assigned agent avatar
5. Click → go to /contact-detail

**Key workflows:**
- Search: filter the Repeating Group by "full_name contains [search input]"
- Status badges: use Conditional formatting — "مهتم" = green, "متابعة" = orange, "غير مهتم" = red

---

### Page: Contact Detail (/contact/:id)

**Layout (2 columns):**

Left column (70%):
1. Client header: Name, phone (click to open WhatsApp), status badge, edit button
2. Tabs: "المعلومات" | "الصفقات" | "النشاط" | "التذكيرات"
   - Info tab: all contact fields in a form
   - Deals tab: repeating group of deals linked to this contact
   - Activity tab: timeline of all activities, + log activity button
   - Reminders tab: upcoming follow-ups, + add reminder button

Right column (30%):
- Quick actions card: "📱 واتساب", "📞 اتصال", "📝 ملاحظة", "📅 تذكير"
- Assigned agent card

**Key workflows:**
- WhatsApp button: open link wa.me/[phone]
- Add activity: popup form → creates Activity record linked to this contact
- Add reminder: popup form → creates FollowUp record

---

### Page: Deals (/deals) — Kanban Board

This is the most important page. A visual pipeline.

**Layout:** Horizontal scroll of columns, one per stage:
- جديد | معاينة | عرض سعر | تفاوض | مغلقة

Each column is a Repeating Group filtered by stage.
Each deal card shows: Title, Client name, Value (SAR), Expected close date.

**Drag-to-move:** Use Bubble's built-in drag-and-drop (in the element properties). When dropped into a new column, trigger a workflow: "Set deal's stage = [column name]"

**Add deal button:** At top of each column, "+" button opens a popup to create a new deal.

---

### Page: Properties (/properties)

**Layout:**
1. Filter bar: Type, City, Price range, Status
2. Property cards grid (with photo, price, area, bedrooms)
3. "+ إضافة عقار" button → opens popup form

---

### Page: Team (/team) — Admin only

Show this page only if current user's role = "admin"

**Layout:**
1. List of agents with: Name, Active deals count, Contacts count, Deals closed this month
2. "+ دعوة وسيط" button → sends invite email via Bubble's email workflow
3. Click agent → see their contacts and deals

---

## Step 4: Key Workflows

### Workflow: New User Signup
Trigger: User signs up
1. Create a new Agency record (or link to existing)
2. Set User's role = "agent"
3. Set Agency's subscription_plan = "trial"
4. Set Agency's subscription_end = today + 30 days
5. Redirect to /onboarding

### Workflow: Follow-up Reminder Email
Trigger: Scheduled — runs every day at 8:00 AM
1. Search for all FollowUp where due_date = today AND is_done = no
2. For each result: send email to assigned_to agent with contact name and note

### Workflow: WhatsApp Lead Capture
1. Create a separate page: /lead-form
2. No login required — public page
3. Simple form: Name, Phone, Interested in (dropdown), Budget
4. On submit: Create a Contact record with status = "جديد" and assigned_to = the agency's first agent
5. Send a WhatsApp notification to agent (via Make.com — see integration section)

### Workflow: Deal Stage Change
Trigger: Deal's stage changes to "مغلقة" AND is_won = yes
1. Create an Activity: type = "صفقة مغلقة"
2. Update Contact's status = "مغلق"
3. (Optional) Send congratulations email to agent

---

## Step 5: WhatsApp Integration via Make.com

Bubble cannot natively send WhatsApp messages. Use Make.com (free tier) as a bridge.

**Setup:**
1. Sign up at make.com (free)
2. Create a Scenario: "Webhook → WhatsApp (via 360dialog)"
3. In Bubble, use the "API Connector" plugin to call your Make.com webhook URL when you need to send a WhatsApp message

**Two key automations to build:**
1. **New lead notification** — When a Contact is created via /lead-form, notify the agent on WhatsApp: "عميل جديد: [name] — رقمه: [phone]"
2. **Daily reminder** — At 8 AM, send agent a WhatsApp summary of today's follow-ups

---

## Step 6: Payments (Moyasar)

For accepting subscriptions, integrate Moyasar (Saudi payment gateway).

1. Sign up at moyasar.com
2. Use Bubble's API Connector to call Moyasar's payment API
3. On successful payment: update Agency's subscription_plan and subscription_end

**Alternatively (easier for launch):** Collect payment manually via bank transfer for the first 20 customers. Add Moyasar integration once you have MRR to justify the complexity.

---

## Step 7: Arabic RTL Setup

In Bubble's Settings → General:
- Set "Direction" to RTL
- Set language to Arabic

For each page:
- In the page properties, set `direction: rtl`
- Use Cairo font: in Styles, set default font to "Cairo" (add via Google Fonts in Settings → SEO/metatags → add `<link>` in header)

**CSS to add in Settings → SEO → Header:**
```html
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap" rel="stylesheet">
<style>
  body, input, button, select, textarea { font-family: 'Cairo', sans-serif !important; direction: rtl; }
</style>
```

---

## Step 8: Deployment Checklist

Before going live:

- [ ] Set a custom domain (waseetcrm.com) in Bubble Settings → Domain
- [ ] Enable SSL (automatic in Bubble)
- [ ] Set up Google Analytics (add GA4 script in header)
- [ ] Test signup → onboarding → add contact → add deal flow
- [ ] Test on mobile (iPhone and Android)
- [ ] Set up support email (support@waseetcrm.com) via Gmail or Zoho Mail (free)
- [ ] Test follow-up reminder emails
- [ ] Set privacy rules on all Data Types (users can only see their agency's data)

---

## Step 9: Privacy Rules (Critical!)

In **Data → Privacy**, set rules so agents can only see their own agency's data:

For every Data Type, add a rule:
- "This [DataType]'s agency's agents contains Current User" → Allow find, Read

For Contacts and Deals, also add:
- Agents can only modify records where assigned_to = Current User (or role = admin)

---

## Build Timeline (Realistic)

| Week | What to Build |
|------|--------------|
| 1 | Setup, Data Types, Login page |
| 2 | Contacts page + Contact Detail page |
| 3 | Deals Kanban board |
| 4 | Dashboard + Properties page |
| 5 | Team page + Follow-up reminders |
| 6 | WhatsApp integration + Lead form |
| 7 | Payments + Polish |
| 8 | Beta test with 5 real users → fix bugs |

**Total: 8 weeks to a working beta.**

---

## Resources

- Bubble.io Academy (free): bubble.io/academy
- Bubble Forum: forum.bubble.io (very active, search in English)
- Khamsat (خمسات): khamsat.com — hire Arabic-speaking Bubble freelancers
- Make.com docs: make.com/en/help
- Moyasar docs: docs.moyasar.com

---

## When to Hire Help

If you get stuck on the Kanban drag-and-drop or the Make.com WhatsApp integration, hire a Bubble freelancer from Khamsat for a fixed task. Budget: 500–1,500 SAR per feature. By the time you need this, your Phase 1 revenue should cover it.
