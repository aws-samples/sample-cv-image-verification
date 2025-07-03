import {
  DescriptionFilteringRule,
  LabelFilteringRule,
} from "@aws-samples/cv-verification-api-client/src";

// Error types for forms
export interface LabelFormErrors {
  imageLabels?: string;
  minConfidence?: string;
  minImageSizePercent?: string;
}

export interface DescriptionFormErrors {
  description?: string;
  minConfidence?: string;
  clusterNumber?: string;
}

// Default Rule Values
export const defaultLabelRule: Omit<
  LabelFilteringRule,
  "id" | "createdAt" | "updatedAt"
> = {
  imageLabels: [],
  minConfidence: 0.5, // Use number type
  minImageSizePercent: 0.1, // Use number type
};

export const defaultDescriptionRule: Omit<
  DescriptionFilteringRule,
  "id" | "createdAt" | "updatedAt"
> = {
  description: "",
  minConfidence: 0.7, // Use number type
  mandatory: false, // Default mandatory to false
};
