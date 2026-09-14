// storage for the enriched chunks and the extracted figures, plus the search service that indexes them.
// deploying this starts billing. basic search is ~$0.10/hour from the moment it exists and there is no stop button, only deletion.

@description('suffix to keep names globally unique')
param suffix string = uniqueString(resourceGroup().id)

param location string = resourceGroup().location

@description('basic is the smallest tier a skillset pipeline actually works on')
@allowed(['free', 'basic'])
param searchSku string = 'basic'

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stawpb${suffix}'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource blob 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource docs 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blob
  name: 'docs'
}

resource images 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blob
  name: 'images'
}

resource search 'Microsoft.Search/searchServices@2025-05-01' = {
  name: 'srch-awpb-${suffix}'
  location: location
  sku: {
    name: searchSku
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    semanticSearch: 'free'
  }
}

output storageAccount string = storage.name
output searchService string = search.name
output searchEndpoint string = 'https://${search.name}.search.windows.net'
output searchPrincipalId string = search.identity.principalId


