# Per-environment backend values for `tofu init -backend-config=backend.dev.hcl`.
# Account <SCJ_AWS_ACCOUNT_ID> = SCJ / dev. Bucket must exist and be versioned + encrypted.
# new-config.sh resolves <SCJ_AWS_ACCOUNT_ID> from config/scj.local.json automatically.
bucket = "<SCJ_AWS_ACCOUNT_ID>-tfstate-us-east-1"
key    = "PROJECT_NAME/dev/terraform.tfstate"
region = "us-east-1"
