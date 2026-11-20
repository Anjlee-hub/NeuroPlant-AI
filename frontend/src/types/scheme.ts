export interface GovernmentScheme {
  id: number;
  name: string;
  category: string;
  department: string;
  status: "active" | "closed" | "unverified";
  description: string;
  benefits: string | null;
  state_codes: string[];
  district_codes: string[];
  crops: string[];
  farmer_categories: string[];
  eligibility_requirements: string[];
  required_documents: string[];
  application_instructions: string | null;
  official_application_url: string | null;
  subsidy_details: string | null;
  source_name: string;
  source_url: string;
  last_verified_at: string | null;
  is_verified: boolean;
}

export interface GovernmentSchemePage {
  items: GovernmentScheme[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  source_status: "scheme_records_available" | "no_scheme_records";
  source_note: string;
}

export interface SchemeFilters {
  state_code?: string;
  district_code?: string;
  crop_name?: string;
  farmer_category?: string;
  category?: string;
  search?: string;
  status?: "active" | "closed" | "unverified";
  page?: number;
  page_size?: number;
}

export interface EligibilityCheckInput {
  state_code?: string;
  district_code?: string;
  crop_name?: string;
  farmer_category?: string;
  landholding_acres?: number;
}

export interface EligibilityCheck {
  scheme_id: number;
  outcome: "potentially_eligible" | "not_eligible" | "unknown";
  matched_rules: string[];
  unmet_rules: string[];
  explanation: string;
  legal_determination: false;
}
