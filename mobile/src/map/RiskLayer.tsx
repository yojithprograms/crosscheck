import { memo, useMemo } from "react";
import { Polyline } from "react-native-maps";

import type { FeatureCollection, LonLat, RiskFeature } from "@/api/types";
import { colors } from "@/theme/colors";
import { toLatLng } from "@/utils/geo";

type Props = {
  layer: FeatureCollection<RiskFeature> | undefined;
  onSelect: (feature: RiskFeature) => void; // tapping a street opens its card
};

type Piece = { key: string; feature: RiskFeature; points: ReturnType<typeof toLatLng>[] };

/** One Polyline per line part of each street. Never color alone: high is thick and solid, medium is dashed. */
export const RiskLayer = memo(function RiskLayer({ layer, onSelect }: Props) {
  const pieces = useMemo<Piece[]>(() => {
    if (!layer) return [];
    return layer.features.flatMap((feature, featureIndex) => {
      const parts: LonLat[][] =
        feature.geometry.type === "LineString" ? [feature.geometry.coordinates] : feature.geometry.coordinates;
      return parts.map((part, partIndex) => ({
        key: `${feature.properties.seg_id}-${featureIndex}-${partIndex}`,
        feature,
        points: part.map(toLatLng),
      }));
    });
  }, [layer]);

  // Medium streets first, so the thicker red lines are drawn on top where they meet.
  const ordered = useMemo(
    () => [...pieces].sort((a, b) => Number(a.feature.properties.risk_class === "high") - Number(b.feature.properties.risk_class === "high")),
    [pieces],
  );

  return (
    <>
      {ordered.map(({ key, feature, points }) =>
        feature.properties.risk_class === "high" ? (
          <Polyline
            key={key}
            coordinates={points}
            strokeColor={colors.riskHigh}
            strokeWidth={6}
            tappable
            onPress={() => onSelect(feature)}
          />
        ) : (
          <Polyline
            key={key}
            coordinates={points}
            strokeColor={colors.riskMedium}
            strokeWidth={4}
            lineDashPattern={[8, 6]}
            tappable
            onPress={() => onSelect(feature)}
          />
        ),
      )}
    </>
  );
});
