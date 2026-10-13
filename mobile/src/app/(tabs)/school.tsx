import { EmptyState } from "@/components/EmptyState";
import { strings } from "@/copy/strings";

export default function SchoolTab() {
  return <EmptyState icon="school-outline" title={strings.placeholders.school.title} body={strings.placeholders.school.body} />;
}
