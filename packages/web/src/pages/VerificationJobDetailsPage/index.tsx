import React from "react";
import { useParams } from "react-router-dom";
import { ContentLayout } from "@cloudscape-design/components";
import { VerificationJobDetails } from "../../components/VerificationJobDetails";

export const VerificationJobDetailsPage: React.FC = () => {
  const { id: jobId } = useParams<{ id: string }>(); // Get jobId from URL params

  return (
    <ContentLayout>
      {/* Pass the jobId (which might be undefined for create) to the details component */}
      <VerificationJobDetails jobId={jobId} />
    </ContentLayout>
  );
};
