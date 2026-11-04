#pragma once
#include "presonus/uc/file_services.hpp"

// Partial portable source class. Original declarations, layout and ARM ABI
// remain limited to the existing evidence; this migration adds no ABI claim.
class MixerSceneLoader : public Presonus::UC::FileRequestHandler {
public:
  using FileRequestHandler::FileRequestHandler;
  ~MixerSceneLoader() override;
};
