import { Ionicons } from "@expo/vector-icons";
import { useEffect, useMemo, useRef, useState } from "react";
import { ActivityIndicator, PixelRatio, ScrollView, StyleSheet, Text, View, useWindowDimensions } from "react-native";
import MapView from "react-native-maps";

import { ApiError } from "@/api/client";
import { useCompareRoutes } from "@/api/hooks";
import type { RouteKind, RouteRequest, School } from "@/api/types";
import { Banner } from "@/components/Banner";
import { PrimaryButton } from "@/components/PrimaryButton";
import { RouteCard } from "@/components/RouteCard";
import { SecondaryButton } from "@/components/SecondaryButton";
import { strings } from "@/copy/strings";
import { RouteLayer } from "@/map/RouteLayer";
import { SchoolMarker } from "@/map/SchoolMarker";
import { StartMarker } from "@/map/StartMarker";
import { useAppStore, type LatLon, type TravelMode } from "@/state/store";
import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";
import { pointToLatLng, regionFitting, toLatLng } from "@/utils/geo";

const STACK_BELOW_WIDTH = 360; // dp: on narrower phones the two route cards stack instead of sitting side by side
const STACK_ABOVE_FONT_SCALE = 1.3; // ...and so they do when the phone's text size is large
// Room around the routes when the map zooms to fit them. The top is larger because the start pin rises above its point.
const FIT_PADDING = { top: 70, right: 50, bottom: 50, left: 50 };

type Props = {
  school: School;
  origin: LatLon;
  mode: TravelMode;
  onChangeStart: () => void; // back to S6
};

/**
 * S8 · the fastest and the lower-risk route side by side: both on the map, a card for each, the server's
 * note about the trade-off, and a way to save the start point. Asks the server once, when it opens.
 */
export function RouteResults({ school, origin, mode, onChangeStart }: Props) {
  const { width } = useWindowDimensions();
  const stacked = width < STACK_BELOW_WIDTH || PixelRatio.getFontScale() > STACK_ABOVE_FONT_SCALE;

  // Ask the server for both routes as soon as this screen opens.
  const compare = useCompareRoutes();
  const { mutate } = compare;
  const request = useMemo<RouteRequest>(
    () => ({ school_id: school.id, origin: { lat: origin.lat, lon: origin.lon }, mode }),
    [school.id, origin, mode],
  );
  useEffect(() => {
    mutate(request);
  }, [mutate, request]);
  const comparison = compare.data;

  // Which route's card is highlighted. The lower-risk route is the one we're offering, so it starts selected.
  const [selected, setSelected] = useState<RouteKind>("lower_risk");

  // Map: first show the start and the school, then zoom to fit both routes when they arrive. Fitting is
  // tried again when the map reports it is ready, in case it finished loading after the routes did.
  const mapRef = useRef<MapView>(null);
  const [mapReady, setMapReady] = useState(false);
  const startPoint = useMemo(() => pointToLatLng(origin), [origin]);
  const schoolPoint = useMemo(() => ({ latitude: school.lat, longitude: school.lon }), [school]);
  const initialRegion = useMemo(() => regionFitting([startPoint, schoolPoint]), [startPoint, schoolPoint]);
  useEffect(() => {
    if (!comparison) return;
    const routePoints = [...comparison.fastest.polyline, ...comparison.lower_risk.polyline].map(toLatLng);
    mapRef.current?.fitToCoordinates([...routePoints, startPoint, schoolPoint], {
      edgePadding: FIT_PADDING,
      animated: true,
    });
  }, [comparison, mapReady, startPoint, schoolPoint]);

  // "Save as my route" keeps this start point and mode on the phone (never on the server).
  const savedRoute = useAppStore((state) => state.savedRoute);
  const saveRoute = useAppStore((state) => state.saveRoute);
  const isSaved =
    savedRoute !== null &&
    savedRoute.mode === mode &&
    savedRoute.origin.lat === origin.lat &&
    savedRoute.origin.lon === origin.lon;

  // A network problem, a timeout, or a server crash is worth retrying. Anything else (a 4xx from the server)
  // means this start point won't work. Step 4.3 gives each of those its own message.
  const failed = compare.isError;
  const canRetry = !(compare.error instanceof ApiError) || compare.error.status === 0 || compare.error.status >= 500;

  return (
    <View style={styles.screen}>
      {failed ? (
        <Banner
          kind="error"
          text={canRetry ? strings.results.failed : strings.results.noRoutes}
          actionLabel={canRetry ? strings.results.retry : undefined}
          onAction={canRetry ? () => mutate(request) : undefined}
        />
      ) : null}

      <View style={styles.map}>
        <MapView
          ref={mapRef}
          style={StyleSheet.absoluteFill}
          initialRegion={initialRegion}
          rotateEnabled={false}
          pitchEnabled={false}
          toolbarEnabled={false}
          onMapReady={() => setMapReady(true)}
        >
          {comparison ? <RouteLayer comparison={comparison} selected={selected} /> : null}
          <StartMarker point={startPoint} />
          <SchoolMarker school={school} />
        </MapView>
      </View>

      <ScrollView style={styles.panel} contentContainerStyle={styles.panelContent}>
        {!comparison && !failed ? (
          <View style={styles.loading} accessibilityLiveRegion="polite">
            <ActivityIndicator color={colors.brand} />
            <Text style={styles.loadingText}>{strings.results.finding}</Text>
          </View>
        ) : null}

        {comparison ? (
          <>
            <View style={[styles.cards, stacked && styles.cardsStacked]}>
              {comparison.same_route ? (
                <RouteCard route={comparison.lower_risk} kind="same" selected />
              ) : (
                <>
                  <View style={stacked ? undefined : styles.half}>
                    <RouteCard
                      route={comparison.fastest}
                      kind="fastest"
                      selected={selected === "fastest"}
                      onPress={() => setSelected("fastest")}
                    />
                  </View>
                  <View style={stacked ? undefined : styles.half}>
                    <RouteCard
                      route={comparison.lower_risk}
                      kind="lower_risk"
                      selected={selected === "lower_risk"}
                      onPress={() => setSelected("lower_risk")}
                    />
                  </View>
                </>
              )}
            </View>

            <View style={styles.note}>
              <Ionicons
                name={comparison.same_route ? "checkmark-circle" : "information-circle"}
                size={20}
                color={colors.infoText}
              />
              <View style={styles.noteTexts}>
                {(comparison.same_route ? [strings.results.sameRoute] : comparison.notes).map((text) => (
                  <Text key={text} style={styles.noteText}>
                    {text}
                  </Text>
                ))}
              </View>
            </View>

            {isSaved ? (
              <View style={styles.saved}>
                <Ionicons name="bookmark" size={20} color={colors.brand} />
                <Text style={styles.savedText}>{strings.results.savedNote}</Text>
              </View>
            ) : (
              <PrimaryButton
                title={strings.results.save}
                icon="bookmark-outline"
                onPress={() => saveRoute({ origin, mode })}
              />
            )}
          </>
        ) : null}

        {comparison || failed ? <SecondaryButton title={strings.results.changeStart} onPress={onChangeStart} /> : null}
        {comparison ? <Text style={styles.smallPrint}>{strings.results.smallPrint}</Text> : null}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  // The map and the panel always split the screen evenly, so the map doesn't change size when the routes
  // arrive (which would throw off the zoom-to-fit).
  map: { flex: 1 },
  panel: { flex: 1, backgroundColor: colors.bg },
  panelContent: { padding: shape.screenPadding, gap: spacing.md },
  loading: { alignItems: "center", gap: spacing.sm, paddingVertical: spacing.xl },
  loadingText: { ...type.body, color: colors.textMuted },
  cards: { flexDirection: "row", gap: spacing.sm },
  cardsStacked: { flexDirection: "column" },
  half: { flex: 1 },
  note: {
    flexDirection: "row",
    gap: spacing.sm,
    backgroundColor: colors.infoBg,
    borderRadius: shape.cardRadius,
    padding: spacing.md,
  },
  noteTexts: { flex: 1, gap: spacing.xs },
  noteText: { ...type.body, color: colors.infoText },
  saved: { flexDirection: "row", alignItems: "center", gap: spacing.sm, minHeight: shape.minTouchTarget },
  savedText: { ...type.body, color: colors.text, flex: 1 },
  smallPrint: { ...type.caption, color: colors.textMuted, textAlign: "center" },
});
