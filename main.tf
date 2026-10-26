terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "azurerm" {
  features {}
}

data "azurerm_client_config" "current" {}

# Resource Group
resource "azurerm_resource_group" "rg" {
  name     = "rg-weebit-production"
  location = "Australia East"
}

# Configure Key Vault for environment deploy
resource "azurerm_key_vault" "kv" {
  name				= "kv-weebit-prod"
  location			= azurerm_resource_group.rg.location
  resource_group_name		= azurerm_resource_group.rg.name
  enabled_for_disk_encryption	= true
  tenant_id			= data.azurerm_client_config.current.tenant_id
  sku_name			= "standard"
}

resource "azurerm_key_vault_access_policy" "terraform_user" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = [
    "Get", "List", "Set", "Delete", "Recover", "Backup", "Restore", "Purge"
  ]
}

# Add placeholder secrets.
resource "azurerm_key_vault_secret" "postgres_user" {
  name         = "PostgresUser"
  value        = azurerm_postgresql_flexible_server.pg.administrator_login
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault_access_policy.terraform_user]
}
resource "azurerm_key_vault_secret" "postgres_password" {
  name         = "PostgresPassword"
  value        = azurerm_postgresql_flexible_server.pg.administrator_password
  key_vault_id = azurerm_key_vault.kv.id
}
resource "azurerm_key_vault_secret" "postgres_db" {
  name         = "PostgresDbName"
  value        = azurerm_postgresql_flexible_server_database.pg_db.name
  key_vault_id = azurerm_key_vault.kv.id
}
resource "azurerm_key_vault_secret" "postgres_port" {
  name         = "PostgresPort"
  value        = "5432"
  key_vault_id = azurerm_key_vault.kv.id
}
resource "azurerm_key_vault_secret" "postgres_host" {
  name         = "PostgresHost"
  value        = azurerm_postgresql_flexible_server.pg.fqdn
  key_vault_id = azurerm_key_vault.kv.id
}
resource "azurerm_key_vault_secret" "backend_host" {
  name         = "BackendHost"
  value        = "app-weebit-api.azurewebsites.net"
  key_vault_id = azurerm_key_vault.kv.id
}
resource "azurerm_key_vault_secret" "backend_port" {
  name         = "BackendPort"
  value        = "8080"
  key_vault_id = azurerm_key_vault.kv.id
}
resource "azurerm_key_vault_secret" "allowed_origins" {
  name         = "AllowedOrigins"
  value        = jsonencode([
    "http://localhost:3080",
    "http://127.0.0.1:3080",
    "https://${azurerm_linux_web_app.frontend.default_hostname}"
  ])
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault_access_policy.terraform_user]
}

# App Service Plan for FastAPI Backend & NextJS Frontend (Linux)
resource "azurerm_service_plan" "asp" {
  name                = "asp-weebit-backend"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = "B1" 
}

# Archive the backend directory into a zip for deployment
data "archive_file" "backend_zip" {
  type		= "zip"
  source_dir	= "${path.module}/backend"
  output_path	= "${path.module}/backend.zip"
  excludes	= [".env", "example.env", "__pycache__", ".gitignore"]
}

data "archive_file" "frontend_zip" {
  type		= "zip"
  source_dir	= "${path.module}/frontend"
  output_path	= "${path.module}/frontend.zip"
  excludes	= [".env", ".env.development.local", ".idea", ".next", "node_modules"]
}

# Linux Web App for FastAPI Backend
resource "azurerm_linux_web_app" "backend" {
  name                = "app-weebit-api"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_service_plan.asp.location
  service_plan_id     = azurerm_service_plan.asp.id

  enabled = false

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.11"
    }
    app_command_line = "python -m uvicorn weebit.main:app --host 0.0.0.0 --port 8080"
  }

  app_settings = {
    "WEBSITE_RUN_FROM_PACKAGE"	= "1"
    "POSTGRES_USER"		= "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.kv.name};SecretName=${azurerm_key_vault_secret.postgres_user.name})"
    "POSTGRES_PASSWORD"		= "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.kv.name};SecretName=${azurerm_key_vault_secret.postgres_password.name})"
    "POSTGRES_DB"		= "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.kv.name};SecretName=${azurerm_key_vault_secret.postgres_db.name})"
    "POSTGRES_PORT"		= "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.kv.name};SecretName=${azurerm_key_vault_secret.postgres_port.name})"
    "POSTGRES_HOST"		= "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.kv.name};SecretName=${azurerm_key_vault_secret.postgres_host.name})"
    "BACKEND_HOST"		= "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.kv.name};SecretName=${azurerm_key_vault_secret.backend_host.name})"
    "BACKEND_PORT"		= "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.kv.name};SecretName=${azurerm_key_vault_secret.backend_port.name})"
    "ALLOWED_ORIGINS"		= "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.kv.name};SecretName=${azurerm_key_vault_secret.allowed_origins.name})"
    "REDIS_URL"			= "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.kv.name};SecretName=${azurerm_key_vault_secret.redis_url.name})"
    "REDIS_PORT"		= "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.kv.name};SecretName=${azurerm_key_vault_secret.redis_port.name})"
    "REDIS_PASSWORD"		= "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.kv.name};SecretName=${azurerm_key_vault_secret.redis_password.name})"
  }
}

# Setup URLs for the backend and the frontend
resource "azurerm_key_vault_secret" "backend_url_sec" {
  name		= "NextPublicApiUrl"
  value		= "https://${azurerm_linux_web_app.backend.default_hostname}"
  key_vault_id	= azurerm_key_vault.kv.id
}
resource "azurerm_key_vault_secret" "frontend_url_sec" {
  name         = "NextPublicFrontendUrl"
  value        = "https://app-weebit-frontend.azurewebsites.net"
  key_vault_id = azurerm_key_vault.kv.id
}

# Allow backend & frontend access to the key vault
resource "azurerm_key_vault_access_policy" "backend_access" {
  key_vault_id	= azurerm_key_vault.kv.id
  tenant_id	= data.azurerm_client_config.current.tenant_id
  object_id	= azurerm_linux_web_app.backend.identity[0].principal_id

  secret_permissions = [
    "Get",
    "List",
  ]
}
resource "azurerm_key_vault_access_policy" "frontend_access" {
  key_vault_id	= azurerm_key_vault.kv.id
  tenant_id	= data.azurerm_client_config.current.tenant_id
  object_id	= azurerm_linux_web_app.frontend.identity[0].principal_id

  secret_permissions = [
    "Get",
    "List",
  ]
}

# Azure Static Web App for Next.js Frontend
resource "azurerm_linux_web_app" "frontend" {
  name			= "app-weebit-frontend"
  resource_group_name	= azurerm_resource_group.rg.name
  location		= azurerm_service_plan.asp.location
  service_plan_id	= azurerm_service_plan.asp.id

  enabled = false
  
  identity {
    type = "SystemAssigned"
  }
  
  site_config {
    application_stack {
      node_version = "20-lts"
    }
    app_command_line = "npm start"
  }
  
  app_settings = {
    "WEBSITE_RUN_FROM_PACKAGE" = "1"
    "NEXT_PUBLIC_FRONTEND_URL" = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.kv.name};SecretName=${azurerm_key_vault_secret.frontend_url_sec.name})"
    "NEXT_PUBLIC_API_URL"      = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.kv.name};SecretName=${azurerm_key_vault_secret.backend_url_sec.name})"
  }
}

# Output important connection details
output "backend_url" {
  value = "https://${azurerm_linux_web_app.backend.default_hostname}"
}

output "frontend_url" {
  value = "https://${azurerm_linux_web_app.frontend.default_hostname}"
}

output "key_vault_name" {
  value = azurerm_key_vault.kv.name
}

resource "random_password" "db_password" {
  length           = 20
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
  min_upper        = 2
  min_lower        = 2
  min_numeric      = 2
  min_special      = 2
}

# Managed PostgreSQL Flexible Server (Burstable B1ms tier for low-cost testing)
resource "azurerm_postgresql_flexible_server" "pg" {
  name                   = "psql-weebit-prod"
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  version                = "15"
  administrator_login    = "weebit_admin"
  administrator_password = random_password.db_password.result
  storage_mb             = 32768
  sku_name               = "B_Standard_B1ms"
}

# PostgreSQL Database inside the server
resource "azurerm_postgresql_flexible_server_database" "pg_db" {
  name      = "weebit_db"
  server_id = azurerm_postgresql_flexible_server.pg.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Allow Azure services to access PostgreSQL (required for Azure Web Apps to connect)
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.pg.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Managed Redis Cache (Basic C0 tier)
resource "azurerm_managed_redis" "redis" {
  name			= "redis-weebit-prod"
  resource_group_name	= azurerm_resource_group.rg.name
  location		= azurerm_resource_group.rg.location
  sku_name		= "Balanced_B0"
  
  default_database {
    access_keys_authentication_enabled	= true
    client_protocol			= "Encrypted"
  }
}

resource "azurerm_key_vault_secret" "redis_url" {
  name         = "RedisUrl"
  value        = azurerm_managed_redis.redis.hostname
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault_access_policy.terraform_user]
}

resource "azurerm_key_vault_secret" "redis_port" {
  name         = "RedisPort"
  value        = tostring(azurerm_managed_redis.redis.default_database[0].port)
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault_access_policy.terraform_user]
}

resource "azurerm_key_vault_secret" "redis_password" {
  name         = "RedisPassword"
  value        = azurerm_managed_redis.redis.default_database[0].primary_access_key
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault_access_policy.terraform_user]
}
