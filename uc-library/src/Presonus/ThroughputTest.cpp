#include "presonus/ThroughputTest.hpp"
#include <new>
#include <stdexcept>
namespace Presonus {
// Original D1 invokes FileStream destruction at native receiver +0x114.
// The actual pinned provider owns the portable member cleanup; offset not
// copied.
ThroughputTest::WriteRecord::~WriteRecord() = default;
ThroughputTest::ThroughputTest(SourcePortTag, int count,
                               Core::IO::Buffer &buffer)
    : Core::Portable::Component("ThroughputTest source port"),
      records_(count, 1) {
  if (count < 0)
    throw std::invalid_argument("negative record count");
  records_.setCount(count);
  buffer_.take(buffer);
}
ThroughputTest::~ThroughputTest() = default;
void ThroughputTest::adoptSourcePortFile(int index, FILE *ownedFile) {
  if (!records_.isValidIndex(index))
    throw std::out_of_range("record index");
  WriteRecord *record = &records_.at(index);
  record->~WriteRecord();
  new (record) WriteRecord(WriteRecord::SourcePortTag{}, ownedFile);
}
} // namespace Presonus
