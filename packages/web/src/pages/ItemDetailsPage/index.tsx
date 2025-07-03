import { useParams } from "react-router-dom";
import { ItemDetails } from "../../components/ItemDetails";
import { useEffect } from "react";
import { useAppLayoutContext } from "../../App";
import { Box, Link } from "@cloudscape-design/components";

export const ItemDetailsPage: React.FC = () => {
  const { id } = useParams();
  const appLayout = useAppLayoutContext();

  useEffect(() => {
    appLayout.setAppLayoutProps({
      breadcrumbs: (
        <>
          <Box display="inline">
            / <Link href="/items">Items</Link> / Edit Item {id}
          </Box>
        </>
      ),
    });
  }, []);

  return (
    <>
      <ItemDetails itemId={id} />
    </>
  );
};
