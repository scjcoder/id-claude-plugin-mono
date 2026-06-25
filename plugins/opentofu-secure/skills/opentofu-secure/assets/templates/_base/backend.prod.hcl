# Per-environment backend values for `tofu init -backend-config=backend.prod.hcl`.
# Account <AWS_ACCOUNT_ID> = InsideDesk / prod. Apply the production safety checklist
# before any mutating command. Bucket must be versioned + encrypted + locked-down.
# new-config.sh resolves <AWS_ACCOUNT_ID> from config/insidedesk.local.json automatically.
bucket = "<AWS_ACCOUNT_ID>-tfstate-us-east-1"
key    = "PROJECT_NAME/prod/terraform.tfstate"
region = "us-east-1"
