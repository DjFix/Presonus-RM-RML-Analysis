#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/corefile.h"
#include "core/public/corebuffer.h"
#include "core/public/corevector.h"
namespace Presonus {
// Partial source-port scope; no original ThroughputTest layout established.
class ThroughputTest : public Core::Portable::Component {
public:
  class WriteRecord {
  public:
    struct SourcePortTag {};
    // Explicit source-port lifecycle: transfers an optional FILE to real Core.
    explicit WriteRecord(SourcePortTag = {}, FILE *ownedFile = nullptr)
        : stream_(ownedFile) {}
    ~WriteRecord();

  private:
    Core::Portable::FileStream stream_;
  };
  struct SourcePortTag {};
  // Independent construction transfers the real buffer ownership flag and fixes
  // record capacity before files are attached. No original constructor
  // asserted.
  ThroughputTest(SourcePortTag, int count, Core::IO::Buffer &buffer);
  ~ThroughputTest() override;
  void adoptSourcePortFile(int index, FILE *ownedFile);

private:
  Core::Vector<WriteRecord> records_;
  Core::IO::Buffer buffer_;
};
} // namespace Presonus
