import { EmptyState } from "@/components/EmptyState";
import { strings } from "@/copy/strings";

export default function ReportStart() {
  return <EmptyState icon="megaphone-outline" title={strings.placeholders.report.title} body={strings.placeholders.report.body} />;
}
