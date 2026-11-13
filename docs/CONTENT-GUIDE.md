# Content guide

This guide is for KLB staff who use the dashboard. No coding is required to
edit text, add books or publish announcements.

## Signing in

1. Open `/admin` on the website.
2. Enter the email address and password issued by the site administrator.
3. Use **Your account** in the sidebar to change your password.

If you cannot sign in, ask an administrator to reset your password. There is no
public self-service password reset page.

## Roles

| Role | Can do |
| --- | --- |
| Editor | Pages, catalogue, news, careers, tenders, resources, enquiries, newsletter subscribers, own password. |
| Administrator | Everything an editor can do, plus **Site settings** and **Users**. |

Editors do not see the settings or user menus, and the API rejects
administrator-only changes.

## The dashboard

The dashboard shows the number of books, news items, open tenders, vacancies,
unread enquiries and newsletter subscribers. It also lists the latest enquiries
and quick links.

## Pages

Every public page is built from **sections** rendered in order.

### Edit an existing page

1. Open **Pages**.
2. Find the page and choose **Edit**.
3. Change the **Page details**:
   - **Title** - the page name shown in the dashboard and used if no browser
     title is set.
   - **URL slug** - the address, for example `about` becomes `/about/`. The home
     page uses `home`.
   - **Browser title** - shown in search results and browser tabs.
   - **Status** - `Draft` hides the page from the public site and the sitemap;
     `Published` makes it live.
   - **Template** - standard pages render sections. The catalogue template is
     reserved for the catalogue page.
   - **Meta description** - one or two sentences for search engines.
4. Edit the sections.
5. Choose **Save changes**.
6. Choose **View page** to confirm the result.

### Add a page

1. Open **Pages** and choose **New page**.
2. Enter a title. The URL slug is generated automatically; you can edit it.
3. Add at least one section.
4. Choose **Create page**.
5. Add the page to the navigation under **Site settings** if it should appear in
   the menu (administrators only).

### Section types

| Type | What it renders |
| --- | --- |
| Rich HTML block | The HTML you write, cleaned automatically. Use this for most content. |
| Book grid | Live books from the catalogue, optionally filtered by featured or new. |
| News list | Published news, newest first. |
| Careers list | Open vacancies. |
| Tenders list | Open tenders. |
| Resources list | Resources, optionally filtered by category. |

The **Settings (JSON)** box controls automatic sections. Every key is optional.
Common keys:

- `kicker` - small label above the heading.
- `heading` - section heading.
- `lede` - introductory sentence.
- `actionLabel` and `actionUrl` - optional link button.
- `limit` - number of records to show.
- `tabs` - `true` on a book grid to show collection tabs.
- `mode` - `featured` or `new` on a book grid.
- `introHtml` - sanitised introductory HTML for list sections.
- `category` - category filter for a resources list.
- `sectionClass` and `sectionId` - CSS class and anchor id for rich HTML blocks.

The editor shows the same hints next to the box. Invalid JSON is rejected before
saving.

### Rich HTML rules

The editor accepts normal HTML, including headings, paragraphs, lists, tables,
links, images and the KLB design classes. Scripts, inline event handlers and
unsafe CSS are removed automatically when you save. Use **Preview HTML** to check
markup before saving.

For images, use files already in the media library or upload them with the file
field. Book covers and resource PDFs can also be uploaded. Paths beginning with
`/assets/` refer to the supplied artwork in `frontend/public/assets`.

### Reorder or remove sections

Use the up and down arrows next to a section. **Remove** deletes it from the page;
saving is required to make that permanent.

## Catalogue

Open **Catalogue** to manage books.

Important fields:

- **Title** and **slug** - the slug is the book's address. Leave it blank to
  generate one from the title.
- **Collection** - CBE, Secondary, Revision, Readers or Tertiary. This drives the
  public filters.
- **Level, subject, language** - free text used by search and filters.
- **Price** - numeric price in Kenyan shillings. Leave blank if there is no price.
- **Cover** - an image path or an upload. Uploads take precedence.
- **Description** - short public description.
- **Featured** and **new arrival** - control the home page and sorting.
- **Status** - draft or published.

Use **Edit** to change a book, **Delete** to remove it. Deleting a book cannot be
undone.

## News

Open **News** to add announcements.

- **Title** - the headline.
- **Slug** - the address under `/news/`. Leave it blank to generate one.
- **Category** - optional label.
- **Summary** - short text shown in lists.
- **Body** - full HTML article.
- **Image** - optional lead image path or upload.
- **Published at** - the display and sitemap date.
- **Featured** - highlights the item on the home page.
- **Status** - draft items are hidden from the public site.

## Careers, tenders and resources

These lists work like news, with fewer fields.

- Careers: department, location, employment type, summary, body, apply URL,
  closing date and open/closed.
- Tenders: category, summary, body, document URL, published date, closing date
  and open/closed.
- Resources: category, description, file URL and an **external** switch for links
  that leave the site.

Automatic list sections only show open careers and tenders. Draft or closed
items stay out of the public lists.

## Enquiries

The contact form creates an enquiry. Open **Enquiries** to read it, change its
status or add an internal note. Status values are used for staff tracking only;
they are never shown to the person who submitted the form.

Never publish personal information from an enquiry. Delete records you no longer
need, in line with the privacy notice.

## Newsletter

Open **Newsletter** to see subscribers. Subscribing twice with the same address
returns a friendly "already on the list" message and does not create a duplicate.
Deactivate or delete addresses that should no longer receive mail.

## Site settings (administrators)

Open **Settings** to edit:

- Site name and tagline.
- Phone numbers, postal address and email addresses.
- Social links and the ebookstore link.
- Announcement bar (leave blank to hide it).
- Footer description, default browser title, default meta description and social
  sharing image.
- Main navigation and footer columns as JSON.

The navigation JSON is a list of items with `label` and `href`. An item may also
have a `panel` with `intro` text and link columns. The footer JSON is a list of
columns, each with a `title` and a list of `[label, href]` pairs. Keep the same
shape as the supplied values. If a save is rejected, restore the last good JSON
and try again.

Changes to global settings appear across the site after saving.

## Users (administrators)

Open **Users** to add staff accounts.

- **Role** - `editor` or `admin`.
- **Password** - at least 10 characters when creating or resetting an account.
- **Active** - deactivate an account instead of deleting it if the person may
  return.

You cannot delete the account you are signed in with. Use **Your account** to
change your own password.

## Publishing checklist

- [ ] Title, browser title and meta description are filled in.
- [ ] The page is set to **Published**.
- [ ] Images load and alt text is meaningful.
- [ ] Links open the intended page.
- [ ] The page appears in the navigation if it should.
- [ ] Prices and dates are correct.
- [ ] The change has been checked on a phone-sized screen.
