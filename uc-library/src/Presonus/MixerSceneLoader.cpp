#include "presonus/MixerSceneLoader.hpp"

#include "core/portable/corepersistence.h"
#include "core/portable/corezipstream.h"
#include "core/public/corememstream.h"
#include <limits>

MixerSceneLoader::MixerSceneLoader(Core::IO::MemoryStream *source,
                                   bool compressed)
    : FileRequestHandler(source),
      compressedSource_(compressed ? source : nullptr) {}

MixerSceneLoader::~MixerSceneLoader() = default;

bool MixerSceneLoader::load(Core::Portable::Attributes &attributes) {
  if (!stream)
    return false;

  if (!compressedSource_) {
    stream->setPosition(0, Core::IO::kSeekSet);
    Core::Portable::Archiver archive(stream);
    return archive.load(attributes);
  }

  const auto bytes = compressedSource_->getBytesWritten();
  if (bytes == 0 || bytes > std::numeric_limits<int>::max())
    return false;
  Core::IO::MemoryStream expanded(8192);
  {
    Core::Portable::ZlibDecompressorStream decompress(&expanded, 15);
    if (decompress.writeBytes(compressedSource_->getBuffer().getAddress(),
                              static_cast<int>(bytes)) < 0)
      return false;
  }
  expanded.setPosition(0, Core::IO::kSeekSet);
  Core::Portable::Archiver archive(&expanded);
  return archive.load(attributes);
}
