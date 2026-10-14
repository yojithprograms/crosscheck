import { memo, useEffect, useState } from "react";
import { Marker } from "react-native-maps";

import type { Hazard } from "@/api/types";
import { NumberBadge } from "@/components/NumberBadge";
import { strings } from "@/copy/strings";

const MARKER_SIZE = 30;
const SNAPSHOT_MS = 500; // how long a marker keeps redrawing so its number is drawn before the map takes its picture

type Props = {
  hazards: Hazard[];
  onSelect: (hazard: Hazard) => void; // tapping a marker opens the hazard card, same as tapping its row
};

function HazardMarker({ hazard, onSelect }: { hazard: Hazard; onSelect: (hazard: Hazard) => void }) {
  // A marker's picture is taken once to keep the map fast. On some phones that happens before the text
  // inside has been drawn, so let it redraw for a moment first.
  const [redrawing, setRedrawing] = useState(true);
  useEffect(() => {
    const timer = setTimeout(() => setRedrawing(false), SNAPSHOT_MS);
    return () => clearTimeout(timer);
  }, []);

  return (
    <Marker
      coordinate={{ latitude: hazard.lat, longitude: hazard.lon }}
      anchor={{ x: 0.5, y: 0.5 }}
      tracksViewChanges={redrawing}
      accessibilityLabel={strings.hazards.markerLabel(hazard.n, hazard.title)}
      zIndex={5}
      onPress={() => onSelect(hazard)}
    >
      <NumberBadge n={hazard.n} kind={hazard.kind} size={MARKER_SIZE} />
    </Marker>
  );
}

/** Numbered circles for the spots on the selected route. The numbers match the list under the map. */
export const HazardMarkers = memo(function HazardMarkers({ hazards, onSelect }: Props) {
  return (
    <>
      {hazards.map((hazard) => (
        <HazardMarker key={`${hazard.n}-${hazard.lat}-${hazard.lon}`} hazard={hazard} onSelect={onSelect} />
      ))}
    </>
  );
});
