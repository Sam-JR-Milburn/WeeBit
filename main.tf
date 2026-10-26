terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
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
  name				= "kv-weebit-prod-xyz"
  location			= azurerm_resource_group.rg.location
  resource_group_name		= azurerm_resource_group.rg.name
  enabled_for_disk_encryption	= true
  tenant_id			= data.azurerm_client_config.current.tenant_id
  sku_name			= "standard"
}

# App Service Plan for FastAPI Backend (Linux)
resource "azurerm_service_plan" "asp" {
  name                = "asp-weebit-backend"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = "B1" 
}

# Archive the backend directory into a zip for deployment
data "archive_file" "backend_zip" {
  type        = "zip"
  source_dir  = "${path.module}/backend"
  output_path = "${path.module}/backend.zip"
}

# Linux Web App for FastAPI Backend
resource "azurerm_linux_web_app" "backend" {
  name                = "app-weebit-api"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_service_plan.asp.location
  service_plan_id     = azurerm_service_plan.asp.id

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
    "WEBSITE_RUN_FROM_PACKAGE" = "1"
  }
}

# Allow backend access to the key vault
resource "azurerm_key_vault_access_policy" "webapp_access" {
  key_vault_id	= azurerm_key_vault.kv.id
  tenant_id	= data.azurerm_client_config.current.tenant_id
  object_id	= azurerm_linux_web_app.backend.identity[0].principal_id

  secret_permissions = [
    "Get",
    "List",
  ]
}


# Azure Static Web App for Next.js Frontend
resource "azurerm_static_web_app" "frontend" {
  name                = "stapp-weebit-frontend"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku_tier            = "Free"
  sku_size            = "Free"
}

# Output important connection details
output "backend_url" {
  value = "https://${azurerm_linux_web_app.backend.default_hostname}"
}

output "frontend_url" {
  value = "https://${azurerm_static_web_app.frontend.default_host_name}"
}

output "key_vault_name" {
  value = azurerm_key_vault.kv.name
}
