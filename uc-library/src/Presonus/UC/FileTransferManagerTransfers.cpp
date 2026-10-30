#include "presonus/dice/packet_services.hpp"
#include "presonus/uc/file_services.hpp"
#include "presonus/uc/file_transfer_manager.hpp"
#include <cmath>
#include <cstring>
#include <limits>
#include <stdexcept>

namespace {
std::int64_t nowMilliseconds() {
  return presonus::dice::packetClockRawTicks() / 1000000;
}
void store64(std::array<std::uint32_t, 14> &words, unsigned index,
             std::int64_t value) {
  std::uint64_t bits;
  std::memcpy(&bits, &value, sizeof(bits));
  words[index] = static_cast<std::uint32_t>(bits);
  words[index + 1] = static_cast<std::uint32_t>(bits >> 32);
}
std::int64_t load64(const std::array<std::uint32_t, 14> &words,
                    unsigned index) {
  const std::uint64_t bits =
      words[index] | (std::uint64_t(words[index + 1]) << 32);
  std::int64_t result;
  std::memcpy(&result, &bits, sizeof(result));
  return result;
}
std::int64_t add64(std::int64_t a, std::int64_t b) {
  const auto bits =
      static_cast<std::uint64_t>(a) + static_cast<std::uint64_t>(b);
  std::int64_t result;
  std::memcpy(&result, &bits, sizeof(result));
  return result;
}
std::int64_t subtract64(std::int64_t a, std::int64_t b) {
  const auto bits =
      static_cast<std::uint64_t>(a) - static_cast<std::uint64_t>(b);
  std::int64_t result;
  std::memcpy(&result, &bits, sizeof(result));
  return result;
}
float floatBits(std::uint32_t bits) {
  float value;
  std::memcpy(&value, &bits, sizeof(value));
  return value;
}
std::uint32_t rawFloat(float value) {
  std::uint32_t bits;
  std::memcpy(&bits, &value, sizeof(bits));
  return bits;
}
int boundedDelay(float value) {
  // Defined source guard. Original equivalence initially covers only finite,
  // representable conversion inputs; exceptional helper cases require proof.
  if (std::isnan(value))
    return 0;
  if (value >= 2147483648.0f)
    return std::numeric_limits<int>::max();
  if (value <= -2147483648.0f)
    return std::numeric_limits<int>::min();
  return static_cast<int>(value);
}
presonus::uc::TransferManagerTransferSink &
requireServices(presonus::uc::TransferManagerTransferSink *sink) {
  if (!sink)
    throw std::logic_error("transfer service port is required");
  return *sink;
}
} // namespace
namespace Presonus::UC {
int FileTransferManager::sendRequest(FileRequestEvent &event,
                                     IFileRequestHandler *handler, int flags) {
  if (!handler)
    return 101;
  auto &services = requireServices(transferSink_);
  const auto mode = static_cast<std::uint32_t>(flags) & 255;
  event.idBits = static_cast<std::uint32_t>(identifiers_.newID());
  auto *value = FileTransfer::create(event, false);
  value->words[3] |= 1;
  value->handler = handler;
  value->words[4] = mode;
  transfers_.append(value);
  store64(value->words, 5, nowMilliseconds());
  if (mode == 1)
    store64(value->words, 9, nowMilliseconds());
  services.sendRequest(event, 0);
  sink_.report(presonus::uc::FileTransferReport::SendRequest, value->words[2],
               value->words[0], value->words[1]);
  return 0;
}
int FileTransferManager::acceptRequest(IFileRequestHandler *handler, int flags,
                                       const FileRequestEvent &event) {
  if (!handler)
    return 101;
  requireServices(transferSink_);
  auto *value = FileTransfer::create(event, true);
  const auto bits = static_cast<std::uint32_t>(flags);
  if (bits & 256)
    value->words[3] |= 2;
  else
    value->words[3] &= ~2u;
  const auto mode = bits & 255;
  value->handler = handler;
  value->words[4] = mode;
  transfers_.append(value);
  store64(value->words, 5, nowMilliseconds());
  if (mode == 1)
    store64(value->words, 9, nowMilliseconds());
  sink_.report(presonus::uc::FileTransferReport::AcceptRequest, value->words[2],
               value->words[0], value->words[1]);
  return 0;
}
bool FileTransferManager::processRead(FileTransfer *value) {
  auto &services = requireServices(transferSink_);
  FileDataEvent event;
  event.header.type = 0x4644;
  event.header.reserved04 = 4128;
  event.header.routeA = value->words[0];
  std::uint32_t bytes = 0;
  if (burst_ > 0) {
    event.header.routeB = value->words[1];
    event.idBits = value->words[2];
    int calls = 0;
    do {
      const bool read = value->handler->readData(event);
      ++calls;
      if (read) {
        const auto count = event.count;
        services.sendData(event, 0);
        bytes += count;
      }
      if (event.partBits != 1)
        return false;
    } while (burst_ > calls);
  }
  std::int32_t signedBytes;
  std::memcpy(&signedBytes, &bytes, sizeof(bytes));
  store64(value->words, 7, add64(load64(value->words, 7), signedBytes));
  return true;
}
void FileTransferManager::sendDataRate(FileTransfer *value, long long now,
                                       int flags) {
  auto &services = requireServices(transferSink_);
  const auto count = load64(value->words, 7);
  const float elapsed =
      static_cast<float>(subtract64(now, load64(value->words, 5))) / 1000.0f;
  float rate = static_cast<float>(count) / elapsed;
  // Both operands originate from finite integer conversions. The original
  // compiler helper canonicalizes their invalid0/0 result to positive qNaN.
  if (std::isnan(rate))
    rate = floatBits(0x7fc00000);
  if (!(rate > 0) && !(static_cast<unsigned>(flags) & 2))
    return;
  FileDataRateEvent event;
  event.header = {0x4653, 32, value->words[0], value->words[1]};
  event.idBits = value->words[2];
  event.wordBits = {rawFloat(rate), value->words[7],
                    static_cast<std::uint32_t>(flags)};
  services.sendRate(event, 0);
}
int FileTransferManager::handleEvent(void *, const Event &header) {
  requireServices(transferSink_);
  if (header.type != 0x4641 && header.type != 0x4644 && header.type != 0x4653)
    return 0;
  // Source event structs are standard-layout with header as first member.
  // Caller must supply the correctly typed live object for the event tag.
  const std::uint32_t id =
      header.type == 0x4641
          ? reinterpret_cast<const FileAbortEvent *>(&header)->idBits
      : header.type == 0x4644
          ? reinterpret_cast<const FileDataEvent *>(&header)->idBits
          : reinterpret_cast<const FileDataRateEvent *>(&header)->idBits;
  FileTransferEvent key;
  key.header = header;
  key.idBits = id;
  auto *value = find(key);
  if (!value)
    return 0;
  if (header.type == 0x4641) {
    sink_.report(presonus::uc::FileTransferReport::Abort, id, 0, 0);
    remove(value);
    return 0;
  }
  if (header.type == 0x4653) {
    const auto &event = *reinterpret_cast<const FileDataRateEvent *>(&header);
    if (value->words[4] != 0 || load64(value->words, 7) <= 0)
      return 0;
    if (event.wordBits[2] & 1)
      value->words[3] |= 8;
    if (event.wordBits[2] & 2)
      value->words[3] |= 16;
    const float rate = floatBits(event.wordBits[0]);
    value->words[11] = rate > floatBits(minimumReceiveRate_)
                           ? event.wordBits[0]
                           : minimumReceiveRate_;
    return 0;
  }
  const auto &event = *reinterpret_cast<const FileDataEvent *>(&header);
  if (value->words[4] != 1) {
    if (event.partBits > 1) {
      sink_.report(presonus::uc::FileTransferReport::TransferError, id, 0, 0);
      remove(value);
    }
    return 0;
  }
  const auto now = nowMilliseconds();
  store64(value->words, 9, now);
  store64(value->words, 7, add64(load64(value->words, 7), event.count));
  if (!value->handler->writeData(event)) {
    sendCancel(value->handler);
    return 0;
  }
  if (event.partBits != 1) {
    if (reporting_ && (value->words[3] & 2))
      sendDataRate(value, now, 2);
    remove(value);
  }
  return 0;
}
void FileTransferManager::processIdle() {
  static bool inCall = false;
  if (transfers_.isEmpty() || inCall)
    return;
  requireServices(transferSink_);
  inCall = true;
  struct Reset {
    bool &flag;
    ~Reset() { flag = false; }
  } reset{inCall};
  const auto now = nowMilliseconds();
  const bool report = reporting_ && subtract64(now, lastReport_) >= 2000;
  if (report)
    lastReport_ = now;
  for (Core::ListIterator<FileTransfer *> i(transfers_); !i.done();) {
    auto *value = i.next();
    if (value->words[4] == 0) {
      if (load64(value->words, 12) > now)
        continue;
      if (value->words[3] & 4) {
        if ((value->words[3] & 16) ||
            subtract64(now, load64(value->words, 9)) > 29999)
          remove(value);
      } else if (!processRead(value)) {
        if (!(value->words[3] & 8))
          remove(value);
        else {
          value->words[3] |= 4;
          store64(value->words, 9, now);
        }
      } else {
        const float rate = floatBits(value->words[11]);
        if (rate > 0) {
          const float bytes = static_cast<float>(load64(value->words, 7));
          const float elapsed =
              static_cast<float>(subtract64(now, load64(value->words, 5))) /
              1000.0f;
          const float delay = ((bytes - elapsed * rate) / rate) * 1000.0f;
          auto next = add64(now, boundedDelay(delay));
          if (next < 0)
            next = 0;
          store64(value->words, 12, next);
        }
      }
    } else if (subtract64(now, load64(value->words, 9)) > 10000) {
      sink_.report(presonus::uc::FileTransferReport::Timeout, value->words[2],
                   0, 0);
      remove(value);
    } else if (report && now > add64(load64(value->words, 5), 1999)) {
      sendDataRate(value, now, (value->words[3] >> 1) & 1);
    }
  }
}
} // namespace Presonus::UC
