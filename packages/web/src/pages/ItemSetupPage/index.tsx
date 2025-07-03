import { Box } from "@cloudscape-design/components";
import { ItemList } from "../../components/ItemList";
import { useAppLayoutContext } from "../../App";
import { useEffect } from "react";

export const SetupItemsPage: React.FC = () => {
  const appLayout = useAppLayoutContext();

  useEffect(() => {
    appLayout.setAppLayoutProps({
      breadcrumbs: <Box>/ Items</Box>,
    });
  }, []);

  return (
    <Box>
      <h1>Setup Items</h1>
      <ItemList />
    </Box>
  );
};
