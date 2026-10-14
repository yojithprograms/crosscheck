import { Ionicons } from "@expo/vector-icons";
import { useEffect, useMemo, useRef, useState } from "react";
import { ActivityIndicator, PixelRatio, ScrollView, StyleSheet, Text, View, useWindowDimensions } from "react-native";
import MapView from "react-native-maps";

import { useCompareRoutes } from "@/api/hooks";
import type { Hazard, RouteKind, RouteRequest, School } from "@/api/types";
import { Banner } from "@/components/Banner";
import { BottomCard } from "@/components/BottomCard";
import { HazardCard } from "@/components/HazardCard";
import { HazardRow } from "@/components/HazardRow";
import { PrimaryButton } from "@/components/PrimaryButton";
import { RouteCard } from "@/components/RouteCard";
import { SecondaryButton } from "@/components/SecondaryButton";
import { strings } from "@/copy/strings";
import { HazardMarkers } from "@/map/HazardMarkers";
import { RouteLayer } from "@/map/RouteLayer";
import { SchoolMarker } from "@/map/SchoolMarker";
import { StartMarker } from "@/map/StartMarker";
import { useAppStore, type LatLon, type TravelMode } from "@/state/store";
import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";
import { friendlyRouteError, type ErrorAction } from "@/utils/errors";
import { pointToLatLng, regionFitting, toLatLng } from "@/utils/geo";

const STACK_BELOW_WIDTH = 360; // dp: on narrower phones the two route cards stack instead of sitting side by side
const STACK_ABOVE_FONT_SCALE = 1.3; // ...and so they do when the phone's text size is large
// Room around the routes when the map zooms to fit them. The top is larger because the start pin rises above its point.
const FIT_PADDING = { top: 70, right: 50, bottom: 50, left: 50 };
const FOCUS_MS = 400; // how long the map takes to slide to a spot when its row or marker is tapped

type Props = {
  school: School;
  origin: LatLon;
  mode: TravelMode;
  onChangeStart: () => void; // back to S6
  onMovePin: () => void; // to S7, with the pin where it was
  onDropPin: () => void; // to S7, starting at the school
  onChangeSchool: () => void; // to S3
  onReportHere: (hazard: Hazard) => void; // to the report flow, starting at this spot
};

/**
 * S8 · the fastest and the lower-risk route side by side: both on the map, a card for each, the server's
 * note about the trade-off, the spots to watch on the selected route (S9 opens from them), and a way to
 * save the start point. Asks the server once, when it opens.
 */
export function RouteResults({
  school,
  origin,
  mode,
  onChangeStart,
  onMovePin,
  onDropPin,
  onChangeSchool,
  onReportHere,
}: Props) {
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
  // The route whose spots are shown. When the fastest route is also the lower-risk one, they are the same.
  const shownKind = comparison?.same_route ? "same" : selected;
  const shownRoute = comparison ? (comparison.same_route ? comparison.lower_risk : comparison[selected]) : null;

  // The spot whose card (S9) is open. It is kept after the card closes so the content doesn't vanish mid-slide.
  const [hazard, setHazard] = useState<Hazard | null>(null);
  const [cardOpen, setCardOpen] = useState(false);
  useEffect(() => {
    setCardOpen(false); // the other route may not have this spot
  }, [selected]);

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

  // A tapped marker or row opens the same card, and the map slides so the spot is in view above it.
  const openHazard = (spot: Hazard) => {
    setHazard(spot);
    setCardOpen(true);
    mapRef.current?.animateCamera({ center: { latitude: spot.lat, longitude: spot.lon } }, { duration: FOCUS_MS });
  };

  // "Save as my route" keeps this start point and mode on the phone (never on the server).
  const savedRoute = useAppStore((state) => state.savedRoute);
  const saveRoute = useAppStore((state) => state.saveRoute);
  const isSaved =
    savedRoute !== null &&
    savedRoute.mode === mode &&
    savedRoute.origin.lat === origin.lat &&
    savedRoute.origin.lon === origin.lon;

  // If the server said no: what to tell the student, and the one button that fits (APP_FLOW §8).
  const failure = compare.isError ? friendlyRouteError(compare.error, school.name) : null;
  const failureButton: Record<ErrorAction, { title: string; onPress: () => void }> = {
    retry: { title: strings.errors.retry, onPress: () => mutate(request) },
    "move-pin": { title: strings.errors.movePin, onPress: onMovePin },
    "drop-pin": { title: strings.errors.dropPin, onPress: onDropPin },
    "change-start": { title: strings.results.changeStart, onPress: onChangeStart },
    "change-school": { title: strings.map.changeSchool, onPress: onChangeSchool },
  };

  return (
    <View style={styles.screen}>
      {failure ? <Banner kind="error" text={failure.message} /> : null}

      <View style={styles.map}>
        <MapView
          ref={mapRef}
          style={StyleSheet.absoluteFill}
          initialRegion={initialRegion}
          rotateEnabled={false}
          pitchEnabled={false}
          toolbarEnabled={false}
          moveOnMarkerPress={false}
          onMapReady={() => setMapReady(true)}
        >
          {comparison ? <RouteLayer comparison={comparison} selected={selected} /> : null}
          {shownRoute ? <HazardMarkers hazards={shownRoute.hazards} onSelect={openHazard} /> : null}
          <StartMarker point={startPoint} />
          <SchoolMarker school={school} />
        </MapView>
      </View>

      <ScrollView style={styles.panel} contentContainerStyle={styles.panelContent}>
        {!comparison && !failure ? (
          <View style={styles.loading} accessibilityLiveRegion="polite">
            <ActivityIndicator color={colors.brand} />
            <Text style={styles.loadingText}>{strings.results.finding}</Text>
          </View>
        ) : null}

        {comparison && shownRoute ? (
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

            <View>
              <Text style={styles.listTitle} accessibilityRole="header">
                {strings.hazards.listTitle[shownKind]}
              </Text>
              {shownRoute.hazards.length === 0 ? (
                <Text style={styles.noHazards}>{strings.hazards.none}</Text>
              ) : (
                shownRoute.hazards.map((spot) => <HazardRow key={spot.n} hazard={spot} onPress={() => openHazard(spot)} />)
              )}
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
            <SecondaryButton title={strings.results.changeStart} onPress={onChangeStart} />
            <Text style={styles.smallPrint}>{strings.results.smallPrint}</Text>
          </>
        ) : null}

        {failure ? (
          <>
            <PrimaryButton {...failureButton[failure.action]} />
            {failure.action !== "change-start" && failure.action !== "change-school" ? (
              <SecondaryButton title={strings.results.changeStart} onPress={onChangeStart} />
            ) : null}
          </>
        ) : null}
      </ScrollView>

      <BottomCard visible={cardOpen} onClose={() => setCardOpen(false)}>
        {hazard ? (
          <HazardCard
            hazard={hazard}
            onReport={() => {
              setCardOpen(false);
              onReportHere(hazard);
            }}
          />
        ) : null}
      </BottomCard>
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
  listTitle: { ...type.headline, color: colors.text, marginBottom: spacing.xs },
  noHazards: { ...type.body, color: colors.textMuted },
  saved: { flexDirection: "row", alignItems: "center", gap: spacing.sm, minHeight: shape.minTouchTarget },
  savedText: { ...type.body, color: colors.text, flex: 1 },
  smallPrint: { ...type.caption, color: colors.textMuted, textAlign: "center" },
});
