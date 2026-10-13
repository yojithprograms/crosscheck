import { Ionicons } from "@expo/vector-icons";
import { memo } from "react";
import { StyleSheet, View } from "react-native";
import { Marker } from "react-native-maps";

import type { School } from "@/api/types";
import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";

/** A teal circle with a school icon at the school's main entrance. */
export const SchoolMarker = memo(function SchoolMarker({ school }: { school: School }) {
  return (
    <Marker
      coordinate={{ latitude: school.lat, longitude: school.lon }}
      anchor={{ x: 0.5, y: 0.5 }}
      tracksViewChanges={false}
      accessibilityLabel={strings.map.schoolMarker(school.name)}
      zIndex={10}
    >
      <View style={styles.circle}>
        <Ionicons name="school" size={20} color={colors.onBrand} />
      </View>
    </Marker>
  );
});

const styles = StyleSheet.create({
  circle: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: colors.brand,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 3,
    borderColor: "white",
  },
});
