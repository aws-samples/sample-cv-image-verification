import { Construct } from "constructs";
import * as location from "aws-cdk-lib/aws-location";
import { Names, RemovalPolicy } from "aws-cdk-lib";

export class LocationConstruct extends Construct {
  public readonly placeIndex: location.CfnPlaceIndex;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    const placeIndexName = Names.uniqueResourceName(this, {
      maxLength: 50,
    });

    // Create a Place Index with Esri as the data provider
    this.placeIndex = new location.CfnPlaceIndex(this, "PlaceIndex", {
      dataSource: "Esri", // Using Esri as the data provider
      indexName: `${placeIndexName}-maps-index`,
      pricingPlan: "RequestBasedUsage", // Pay per request
      dataSourceConfiguration: {
        // Configure the data source to include address and position search
        intendedUse: "SingleUse",
      },
      description: "Place index for geocoding and reverse geocoding",
    });
  }
}
