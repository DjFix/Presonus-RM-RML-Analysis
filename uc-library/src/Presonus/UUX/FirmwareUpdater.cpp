#include "core/portable/corefile.h"
#include "core/portable/corepersistence.h"
#include "core/system/corethread.h"
#include "core/system/coretime.h"
#include "presonus/application/SimpleReader.hpp"
#include "presonus/uux/FirmwareUpdaterPaths.hpp"
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <curl/curl.h>
#include <limits>

namespace {
Core::CString128 responsePath() {
  Core::Portable::FileName temp;
  Core::Portable::FileUtils::getTempDir(temp);
  Core::CString128 path(temp.str());
  path += "response";
  return path;
}
} // namespace
// Original application helper, not a libcurl implementation. Host libcurl's
// size_t callback uses the separate adapter below; original unsigned signature
// and per-role identities remain recorded in the recovery evidence.
[[gnu::used]] static unsigned curlRequestCallback(void *data, unsigned size,
                                                  unsigned count, void *) {
  const auto path = responsePath();
  Core::Portable::FileUtils::deleteFile(path.str());
  Core::Portable::FileStream file;
  const unsigned bytes = size * count;
  if (file.create(path.str())) {
    file.writeBytes(data, bytes);
    file.close();
  }
  return bytes;
}
namespace {
std::size_t hostCurlRequestCallback(char *data, std::size_t size,
                                    std::size_t count, void *user) {
  if (size > std::numeric_limits<unsigned>::max() ||
      count > std::numeric_limits<unsigned>::max())
    return 0;
  return curlRequestCallback(data, static_cast<unsigned>(size),
                             static_cast<unsigned>(count), user);
}
} // namespace
namespace Presonus::UUX {
FirmwareUpdater::FirmwareUpdater(int product, int serial,
                                 FirmwareUpdateListener *listener)
    : listener(listener), animate(true),
      localArchiveDirectory("/home/root/DFU"),
      usbImagePath("/media/sda1/upgrade.bin"),
      upgradeUrl("https://user.presonus.com/upgrade"),
      completionMessage("Power Cycle the Mixer") {
  serialNumber.appendFormat("%d", serial);
  static const char *const products[] = {"sl3242ai", "sl2442ai", "sl1642ai",
                                         "rm32",     "rm16",     "cs18"};
  static const char *const prefixes[] = {"SL3E", "SL2E", "SL1E",
                                         "RM3E", "RM1E", "CS8H"};
  if (product >= 20 && product <= 25) {
    productId = products[product - 20];
    serialNumber.insert(0, prefixes[product - 20]);
  }
}
FirmwareUpdater::~FirmwareUpdater() = default;
int FirmwareUpdater::prepareFirmwareRequestFields() {
  Core::Portable::FileStream mac;
  if (mac.open("/sfs/hwaddr.txt", Core::IO::kReadMode | Core::IO::kWriteMode)) {
    Presonus::SimpleReader reader(mac);
    reader.getNextWord(macAddress, ' ');
    mac.close();
  } else {
    macAddress += "00:00:00:00:00:00";
  }
  firmwareVersion = sourceFirmwareVersion;
  timestamp = "";
  // Intentional provider adaptation: old GetAbsoluteTime() low unsigned word
  // is represented by pinned SystemClock seconds, with uint32 wrapping.
  timestamp.appendFormat(
      "%u", static_cast<std::uint32_t>(Core::SystemClock::getSeconds()));
  requestKey = "x_TmXsFHBa4AJukp";
  requestKey += serialNumber;
  requestKey += firmwareVersion;
  requestKey += timestamp;
  Core::CString128 command;
  command.appendFormat("echo -n \"%s\" | md5sum > ", requestKey.str());
  command.appendFormat("%s", "md5scratch");
  ::system(command.str());
  int result = -1;
  Core::Portable::FileStream hash;
  if (hash.open("md5scratch", Core::IO::kReadMode | Core::IO::kWriteMode)) {
    Presonus::SimpleReader reader(hash);
    reader.getNextWord(requestKey, ' ');
    hash.close();
    result = 0;
  }
  Core::Portable::FileUtils::deleteFile("md5scratch");
  return result;
}
int FirmwareUpdater::doNetworkFirmwareUpdate() {
  Core::CString64 requestUrl("http://my.presonus.com/api/");
  requestUrl +=
      requestEndpoint.isEmpty() ? "mixer/rm_upgrade" : requestEndpoint.str();
  Core::CString256 message("Please wait");
  if (listener)
    listener->onProgress("Contacting PreSonus for updates", message.str(), 0.f);
  Core::Threads::CurrentThread::sleep(3000);
  if (curl_global_init(CURL_GLOBAL_ALL) != CURLE_OK)
    return 8;
  // Native leaves global Curl initialized if request preparation fails.
  if (prepareFirmwareRequestFields() < 0)
    return 8;
  Core::CString256 post;
  post.appendFormat("mac=%s", macAddress.str());
  post.appendFormat("&serial=%s", serialNumber.str());
  post.appendFormat("&product_id=%s", productId.str());
  post.appendFormat("&product_family=%s", "StudioLiveAI");
  post.appendFormat("&fw_version=%s", firmwareVersion.str());
  post.appendFormat("&key=%s", requestKey.str());
  post.appendFormat("&timestamp=%s", timestamp.str());
  int result = 8;
  if (auto *curl = curl_easy_init()) {
    curl_easy_setopt(curl, CURLOPT_URL, requestUrl.str());
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, hostCurlRequestCallback);
    curl_easy_setopt(curl, CURLOPT_POST, 1L);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, post.str());
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 60L);
    // Native ignores CURLcode and subsequently reads the response file.
    (void)curl_easy_perform(curl);
    curl_easy_cleanup(curl);
    Core::Portable::Attributes response(
        Core::Portable::AttributeAllocator::getDefault());
    auto path = responsePath();
    if (Core::Portable::ArchiveUtils::loadFromFile(response, path.str())) {
      const int code = response.getInt("result_code");
      Core::CString256 uri(response.getString("firmware_URI"));
      if (code == -1)
        result = 9;
      else if (code == 0) {
        if (uri.length() <= 1)
          result = 10;
        else {
          Core::CString256 archive;
          const char *slash = std::strrchr(uri.str(), '/');
          archive = slash ? slash + 1 : uri.str();
          // Native removes the character immediately before the first matching
          // archive substring, rather than simply splitting at the last slash.
          if (const char *match = std::strstr(uri.str(), archive.str())) {
            const auto index = match - uri.str() - 1;
            if (index >= 0 && index < uri.length())
              uri.getBuffer()[index] = 0;
          }
          Core::CString256 command;
          command.appendFormat("./fw-upgrade.sh %s %s", uri.str(),
                               archive.str());
          result =
              spinUpgradeDisplay(executeBashUpgradeScript(command.str())) == 0
                  ? 0
                  : 8;
        }
      }
    }
  }
  curl_global_cleanup();
  return result;
}
int FirmwareUpdater::updateFirmware() {
  if (listener)
    listener->doAlert("Firmware Update", "Checking for update...",
                      "Do not power off the device");
  int result = doLocalFirmwareUpdate();
  if (result != 0) {
    result = doUsbFirmwareUpdate();
    if (result != 0)
      result = doNetworkFirmwareUpdate();
  }
  if (!listener)
    return result;
  listener->dismissAlert();
  switch (result) {
  case 0:
    listener->doAlert("Firmware update complete", completionMessage.str(), "");
    break;
  case 1:
    listener->doAlert("Unable to mount the USB stick", "Check the USB stick",
                      completionMessage.str());
    break;
  case 2:
    listener->doAlert("Can't find firmware update", "Upgrade Aborted",
                      completionMessage.str());
    break;
  case 3:
    listener->doAlert("Unable to extract update", "Upgrade Aborted",
                      completionMessage.str());
    break;
  case 4:
    listener->doAlert("Checksum failed", "Upgrade Aborted",
                      completionMessage.str());
    break;
  case 5:
    listener->doAlert("Firmware backup failed", "Upgrade Aborted",
                      completionMessage.str());
    break;
  case 6:
    listener->doAlert("Firmware update failed", "Upgrade Aborted",
                      completionMessage.str());
    break;
  case 7:
    listener->doAlert("Unable to unmount the drive", completionMessage.str(),
                      "");
    break;
  case 8:
    listener->doAlert("Network update failed.", completionMessage.str(), "");
    break;
  case 9:
    listener->doAlert("Device not registered.", "Register at presonus.com", "");
    break;
  case 10:
    listener->doAlert("Firmware is current.", "No changes were made.", "");
    break;
  default:
    listener->doAlert("Unknown error", "Upgrade Aborted",
                      completionMessage.str());
    break;
  }
  return result;
}
} // namespace Presonus::UUX
