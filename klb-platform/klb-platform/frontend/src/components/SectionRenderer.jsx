import BookGridSection from "./sections/BookGridSection.jsx";
import CareersListSection from "./sections/CareersListSection.jsx";
import NewsListSection from "./sections/NewsListSection.jsx";
import ResourcesListSection from "./sections/ResourcesListSection.jsx";
import TendersListSection from "./sections/TendersListSection.jsx";

export default function SectionRenderer({ section }) {
  switch (section.kind) {
    case "book_grid":
      return <BookGridSection section={section} />;
    case "news_list":
      return <NewsListSection section={section} />;
    case "careers_list":
      return <CareersListSection section={section} />;
    case "tenders_list":
      return <TendersListSection section={section} />;
    case "resources_list":
      return <ResourcesListSection section={section} />;
    case "html":
    default:
      return <div className="cms-section" dangerouslySetInnerHTML={{ __html: section.html }} />;
  }
}
