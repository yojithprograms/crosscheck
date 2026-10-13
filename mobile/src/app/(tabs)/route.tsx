import { EmptyState } from "@/components/EmptyState";
import { strings } from "@/copy/strings";

export default function RouteTab() {
  return <EmptyState icon="navigate-outline" title={strings.placeholders.route.title} body={strings.placeholders.route.body} />;
}
