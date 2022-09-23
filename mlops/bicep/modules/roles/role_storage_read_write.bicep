// This BICEP script will create a custom RBAC role with read/write actions.

// resource group must be specified as scope in az cli or module call
targetScope = 'subscription'

// Array of actions for the roleDefinition'
var singleDirectionWriteActions = [
  // see https://learn.microsoft.com/en-us/azure/storage/blobs/authorize-data-operations-portal#use-the-account-access-key
  // need the 2 below to get token to mount data
  'Microsoft.Storage/storageAccounts/listkeys/action'
  'Microsoft.Storage/storageAccounts/ListAccountSas/action'
  // read the 'container' (not the data)
  'Microsoft.Storage/storageAccounts/blobServices/containers/read'
]
var singleDirectionWriteDataActions = [
  'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'
  'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write'
  'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action'
]

// Array of notActions for the roleDefinition
var singleDirectionWriteNotActions = [
  'Microsoft.Storage/storageAccounts/blobServices/containers/delete'
]
var singleDirectionWriteNotDataActions = [
  'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete'
]

// get a guid
var sinlgleDirectionWriteRoleDefName = guid(
  subscription().id,
  string(singleDirectionWriteActions),
  string(singleDirectionWriteDataActions),
  string(singleDirectionWriteNotActions),
  string(singleDirectionWriteNotDataActions)
)

resource roleDefinition 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: sinlgleDirectionWriteRoleDefName
  // scope: resourceGroup()
  properties: {
    roleName: 'FL Demo - Storage Read/Write'
    description: 'Can read and write a blob into a storage container.'
    type: 'customRole'
    permissions: [
      {
        actions: singleDirectionWriteActions
        notActions: singleDirectionWriteNotActions
        dataActions: singleDirectionWriteDataActions
        notDataActions: singleDirectionWriteNotDataActions
      }
    ]
    assignableScopes: [
      subscription().id
    ]
  }
}

// return role id
output roleDefinitionId string = roleDefinition.id