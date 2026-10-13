import { Banner } from "@/components/Banner";
import { useServerWake } from "@/api/hooks";
import { strings } from "@/copy/strings";

/** Shows the "Waking up the server…", offline, or can't-reach banner (nothing when all is well). */
export function ServerBanner() {
  const { state, retry } = useServerWake();
  if (state === "waking") return <Banner kind="info" text={strings.banner.waking} />;
  if (state === "offline") return <Banner kind="warn" text={strings.banner.offline} actionLabel={strings.banner.retry} onAction={retry} />;
  if (state === "failed") return <Banner kind="error" text={strings.banner.unreachable} actionLabel={strings.banner.retry} onAction={retry} />;
  return null;
}
