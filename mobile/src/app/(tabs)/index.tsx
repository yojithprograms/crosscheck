import { EmptyState } from "@/components/EmptyState";
import { strings } from "@/copy/strings";

export default function MapTab() {
  return <EmptyState icon="map-outline" title={strings.placeholders.map.title} body={strings.placeholders.map.body} />;
}
