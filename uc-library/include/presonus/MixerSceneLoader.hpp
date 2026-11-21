#pragma once
#include "presonus/uc/file_services.hpp"

namespace Core::IO {
class MemoryStream;
}

// Partial portable source class. Original declarations, layout and ARM ABI
// remain limited to the existing evidence; this migration adds no ABI claim.
class MixerSceneLoader : public Presonus::UC::FileRequestHandler {
public:
  using FileRequestHandler::FileRequestHandler;
  MixerSceneLoader(Core::IO::MemoryStream *source, bool compressed);
  ~MixerSceneLoader() override;
  bool load(Core::Portable::Attributes &attributes);

private:
  Core::IO::MemoryStream *compressedSource_ = nullptr;
};
