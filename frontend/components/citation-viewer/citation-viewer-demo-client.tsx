"use client";

import { useState } from "react";
import { CitationViewer, CitationData } from "./citation-viewer";

export default function CitationViewerDemoClient({
  citation,
}: {
  citation?: CitationData;
}) {
  const [currentCitation, setCurrentCitation] = useState<
    CitationData | undefined
  >(citation);

  async function handleVerifyAgain(c: CitationData) {
    // Simulate a 1.5s async verification call
    await new Promise((resolve) => setTimeout(resolve, 1500));
    setCurrentCitation({
      ...c,
      verificationStatus: "verified",
      verifiedAt: new Date().toLocaleString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        timeZoneName: "short",
      }),
    });
  }

  return (
    <CitationViewer
      citation={currentCitation}
      onVerifyAgain={handleVerifyAgain}
    />
  );
}
