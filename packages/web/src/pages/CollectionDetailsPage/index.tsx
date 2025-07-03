import { Box, Link } from "@cloudscape-design/components";
import { useAppLayoutContext } from "../../App";
import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useGetCollection } from "../../hooks/Collections";
import CollectionDetails from "../../components/CollectionDetails";

export const CollectionDetailsPage: React.FC = () => {
  const appLayout = useAppLayoutContext();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { data: collection } = useGetCollection(id);

  useEffect(() => {
    appLayout.setAppLayoutProps({
      breadcrumbs: (
        <>
          <Box display="inline">
            / <Link href="/collections">Collections</Link> / Edit Collection{" "}
            {collection ? collection.collection.description : id}
          </Box>
        </>
      ),
    });
  }, []);

  const handleSave = (collectionId: string) => {
    navigate(`/collection/${collectionId}`);
  };

  const handleCancel = () => {
    navigate("/collections");
  };

  return (
    <Box padding="m">
      <CollectionDetails
        collection={collection?.collection}
        onSave={handleSave}
        onCancel={handleCancel}
      />
    </Box>
  );
};
