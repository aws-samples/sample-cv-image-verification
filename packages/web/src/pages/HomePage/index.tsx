import { Box, Header, SpaceBetween } from "@cloudscape-design/components";
import { FC } from "react";

export const HomePage: FC = () => {
  return (
    <>
      <SpaceBetween size={"m"}>
        <Box>
          <img style={{ maxWidth: "200px" }} src="assets/foreman.png"></img>
        </Box>
        <Header>Computer Vision Image Verification</Header>

        <Box>
          This is an AWS samples solution that helps organizations automatically
          verify and validate image sets using AI. The solution analyzes images
          against predefined image descriptions using computer vision and
          natural language to confirm that images meet specified requirements,
          dramatically reducing manual review time while improving accuracy.
        </Box>
      </SpaceBetween>
    </>
  );
};
