from foundry_local_sdk import Configuration, FoundryLocalManager

config = Configuration(app_name="ListModels")
FoundryLocalManager.initialize(config)

manager = FoundryLocalManager.instance
catalog = manager.catalog.list_models()

for m in catalog:
    print(m.model_id if hasattr(m, "model_id") else vars(m))