/**********************************************************************************************************************
 *  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                *
 *                                                                                                                    *
 *  Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance        *
 *  with the License. A copy of the License is located at                                                             *
 *                                                                                                                    *
 *     https://aws.amazon.com/asl/                                                                                    *
 *                                                                                                                    *
 *  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES *
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    *
 *  and limitations under the License.                                                                                *
 **********************************************************************************************************************/

/*! Copyright [Amazon.com](http://amazon.com/), Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0 */
import * as React from "react";
import { Route, Routes as ReactRoutes } from "react-router-dom";
import { HomePage } from "./pages/HomePage";
import { CollectionListPage } from "./pages/CollectionsListPage";
import { CollectionDetailsPage } from "./pages/CollectionDetailsPage";
import { VerificationJobsListPage } from "./pages/VerificationJobsListPage";
import { VerificationJobDetailsPage } from "./pages/VerificationJobDetailsPage";
import { Config } from "./pages/Config";
import { SetupItemsPage } from "./pages/ItemSetupPage";
import { ItemDetailsPage } from "./pages/ItemDetailsPage";
import { AgentListPage } from "./pages/AgentListPage";
import { AgentDetailsPage } from "./pages/AgentDetailsPage";

/**
 * Defines the Routes.
 */
const Routes: React.FC = () => {
  return (
    <ReactRoutes>
      <Route path="/items" element={<SetupItemsPage />} />
      <Route path="/collections" element={<CollectionListPage />} />
      <Route path="/collection/:id" element={<CollectionDetailsPage />} />
      <Route path="/itemdetail/:id" element={<ItemDetailsPage />} />
      <Route path="/newitem" element={<ItemDetailsPage />} />
      <Route path="/newjob" element={<VerificationJobDetailsPage />} />
      <Route path="/job/:id" element={<VerificationJobDetailsPage />} />
      <Route path="/verificationjobs" element={<VerificationJobsListPage />} />
      <Route path="/agents" element={<AgentListPage />} />
      <Route path="/agent/:id" element={<AgentDetailsPage />} />
      <Route path="/agent/new" element={<AgentDetailsPage />} />
      <Route path="/config" element={<Config />} />
      <Route path="*" element={<HomePage />} />
    </ReactRoutes>
  );
};

export default Routes;
