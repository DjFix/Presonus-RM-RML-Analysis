#pragma once
#include "core/public/corestringbuffer.h"
#include "core/public/corevector.h"
#include <zlib.h>

namespace presonus::application {
struct ResourceAccess;
}
namespace Presonus {
class ResourceLibrary;
// Source-port metadata/storage; original layout and access remain unknown.
// Stream methods are source-ported with declaration and native zlib ABI limits.
class FirmwareBundle {
public:
  // Ordinary int return spellings remain declaration-pending.
  int openBinImage();
  int closeBinImage();
  int readBinImageBlock(unsigned char *, int);

private:
  friend class ResourceLibrary;
  friend struct presonus::application::ResourceAccess;
  Core::CStringBuffer<64> name_;
  unsigned int version_;
  const unsigned char *image_;
  int image_size_;
  bool compressed_;
  z_stream stream_; // Actual zlib storage; no initial tail values are claimed.
};

class ResourceLibrary {
public:
  ResourceLibrary();
  ~ResourceLibrary();
  // Ordinary returns/access declarations are unencoded and remain pending.
  FirmwareBundle *get(const char *);
  unsigned int getRequiredVersion(const char *);
  void addFirmware(const char *, unsigned int, const unsigned char *, int,
                   bool);
  void addFirmware(FirmwareBundle *);

private:
  friend struct presonus::application::ResourceAccess;
  Core::Vector<FirmwareBundle *> bundles_;
};
} // namespace Presonus
