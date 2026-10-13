import { EmptyState } from "@/components/EmptyState";
import { strings } from "@/copy/strings";

export default function Settings() {
  return <EmptyState icon="settings-outline" title={strings.placeholders.settings.title} body={strings.placeholders.settings.body} />;
}
