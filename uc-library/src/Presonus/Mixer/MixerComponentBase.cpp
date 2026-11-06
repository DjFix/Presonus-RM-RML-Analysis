#include "presonus/mixer/MixerComponentBase.hpp"
#include "core/portable/corefile.h"
#include "core/portable/coreparams.h"
#include "core/portable/corepersistence.h"
#include "core/portable/coreworker.h"
#include "core/public/corestringbuffer.h"
#include "presonus/mixer/PermissionsComponent.hpp"
#include <cstring>
#include <memory>
#include <stdexcept>
namespace Presonus::Mixer {
std::uint32_t MixerComponentBase::getSelectedChannel() const {
  return selectedChannel;
}
void MixerComponentBase::validateClients() const {
  if (clientsBound_ &&
      clientCount != static_cast<std::uint32_t>(clients_.count()))
    throw std::logic_error("inconsistent client collection/count binding");
}
void MixerComponentBase::bindClients(
    const Core::Vector<const UC::ClientSubscription *> &clients) {
  clients_ = clients;
  clientCount = static_cast<std::uint32_t>(clients_.count());
  clientsBound_ = true;
}
std::uint32_t MixerComponentBase::numClients() const {
  validateClients();
  return clientCount;
}
const UC::ClientSubscription *MixerComponentBase::getClient(int index) const {
  validateClients();
  if (!clientsBound_ && clientCount != 0)
    throw std::logic_error("client collection must be bound");
  return index < 0 || index >= clients_.count() ? nullptr : clients_.at(index);
}
std::uint32_t MixerComponentBase::numHWMicLineIn() const {
  if (inputChannelNamingBound)
    validateInputChannelBinding();
  return hardwareMicLineInputs;
}
const char *MixerComponentBase::getCompanyName() const { return "presonus"; }
std::uint32_t MixerComponentBase::getSpectrumSendSlot() const {
  return numHWMicLineIn() + std::uint32_t{12};
}
void MixerComponentBase::setTryingToQuit() { tryingToQuit = true; }
Core::Portable::FileName
MixerComponentBase::getDataDir(const char *subdir) const {
  Core::Portable::FileName path(applicationDataRoot);
  if (path.isEmpty())
    Core::Portable::FileUtils::getDataDir(path, false);
  path.descend(getCompanyName());
  Core::Portable::FileUtils::makeDirectory(path.str());
  path.descend(deviceDataFolder.str());
  Core::Portable::FileUtils::makeDirectory(path.str());
  if (subdir) {
    path.descend(subdir);
    Core::Portable::FileUtils::makeDirectory(path.str());
  }
  return path;
}
void MixerComponentBase::validateInputChannelBinding() const {
  if (!inputChannelNamingBound || !channelParameters || !channelIdentity)
    throw std::logic_error("missing input channel naming binding");
  if (hardwareMicLineInputs !=
      static_cast<std::uint32_t>(inputChannels.count()))
    throw std::logic_error("inconsistent input channel count binding");
  for (int i = 0; i < inputChannels.count(); ++i)
    if (!inputChannels.at(i) || !channelParameters(inputChannels.at(i)))
      throw std::logic_error("missing channel parameter binding");
}
void MixerComponentBase::bindInputChannelNaming(
    std::function<Core::Portable::Component *(ChannelComponent *)> resolver) {
  channelParameters = std::move(resolver);
  inputChannelNamingBound = true;
  try {
    validateInputChannelBinding();
  } catch (...) {
    inputChannelNamingBound = false;
    throw;
  }
}
bool MixerComponentBase::isSlave() {
  return cascadeParameters->getParameterByTag(5)->getValue() == 2.f;
}
void MixerComponentBase::onCascadeStateChange() {
  validateChannelNaming();
  cascadeStatePending = false;
}
void MixerComponentBase::validateChannelNaming() {
  validateInputChannelBinding();
  const auto slave = isSlave();
  const auto count = static_cast<std::int32_t>(hardwareMicLineInputs);
  const std::uint32_t offset = slave ? hardwareMicLineInputs : 0;
  for (std::int32_t i = 0; i < count; ++i) {
    auto *channel = inputChannels.at(i);
    auto *parameters = channelParameters(channel);
    auto *number = parameters->getParameterByTag(0);
    auto *label = parameters->getParameterByTag(1);
    auto *name = parameters->getParameterByTag(2);
    if (!number || !label || !name)
      continue;
    Core::CStringBuffer<32> oldLabel, oldName, first, second, updated, digits;
    label->toString(oldLabel.getBuffer(), 32);
    name->toString(oldName.getBuffer(), 32);
    const std::uint32_t index =
        static_cast<std::uint32_t>(channelIdentity(channel).second) + 1U;
    first.appendFormat("Ch. %d", static_cast<std::int32_t>(index));
    second.appendFormat(
        "Ch. %d", static_cast<std::int32_t>(index + hardwareMicLineInputs));
    updated.appendFormat("Ch. %d", static_cast<std::int32_t>(index + offset));
    digits.appendFormat("%d", static_cast<std::int32_t>(index + offset));
    const bool defaultName = std::strcmp(oldName.str(), first.str()) == 0 ||
                             std::strcmp(oldName.str(), second.str()) == 0;
    label->fromString(updated.str(), false);
    number->fromString(digits.str(), false);
    if (defaultName && std::strcmp(oldName.str(), updated.str()) != 0)
      name->fromString(updated.str(), false);
  }
}
void MixerComponentBase::resetPermissionsPW() {
  if (permissions)
    permissions->resetPermissionsPW();
}
Core::Portable::FileName
MixerComponentBase::findLocalFile(Core::ConstString name) const {
  if (!saveServices.localFile)
    throw std::logic_error("local file policy required");
  return saveServices.localFile(name);
}
void MixerComponentBase::presetSaved(Core::Portable::FileName filename,
                                     const char *name, const char *type,
                                     int count) {
  if (!saveServices.completed)
    throw std::logic_error("preset completion policy required");
  saveServices.completed(filename, name, type, count);
}
bool MixerComponentBase::savePreset(const Core::Portable::FileName &filename,
                                    const char *displayName,
                                    Core::ConstString componentName) {
  using namespace Core::Portable;
  FileName extension;
  filename.getExtension(extension);
  int type = 4;
  const struct {
    const char *extension;
    int type;
  } types[] = {
      {"scene", 0}, {"channel", 4}, {"geq", 5}, {"reverb", 6}, {"delay", 7}};
  for (const auto &entry : types)
    if (std::strcmp(extension.str(), entry.extension) == 0) {
      type = entry.type;
      break;
    }
  if (type == 0)
    return saveScene(filename, displayName, true);
  if (!saveServices.parameters || !saveServices.inspectCache ||
      !saveServices.saveFlags || !saveServices.completed)
    throw std::logic_error("preset application bindings required");
  const auto cache = saveServices.inspectCache(filename);
  if (cache.found) {
    if (!saveServices.refreshCache)
      throw std::logic_error("cache refresh policy required");
    if (!cache.obsoleteFile.isEmpty() &&
        std::strcmp(cache.obsoleteFile.str(), filename.str()) != 0)
      FileUtils::deleteFile(cache.obsoleteFile.str());
    saveServices.refreshCache(cache);
  }
  const auto outputFile = findLocalFile(filename.str());
  auto *component = saveServices.parameters->lookupChild(componentName.str());
  if (!component)
    return false;
  const int flags = saveServices.saveFlags(type, component);
  Attributes attributes(AttributeAllocator::getDefault());
  AttributesBuilder builder(attributes);
  OutputStorage storage(builder);
  if (saveServices.configureStorage)
    saveServices.configureStorage(storage, flags);
  else if (flags != 0)
    throw std::logic_error("storage flags adaptation required");
  component->save(storage);
  class StorageCompletionHandler final : public FileIOCompletionHandler {
    MixerComponentBase &owner;
    FileName name;
    Core::CStringBuffer<64> extension;
    int count;

  public:
    StorageCompletionHandler(MixerComponentBase &owner, const char *name,
                             const FileName &extension, int count)
        : owner(owner), name(name), extension(extension.str()), count(count) {}
    ~StorageCompletionHandler() override = default;
    void onSaveFileCompleted(Core::CStringPtr filename) override {
      owner.presetSaved(FileName(filename), name.str(), extension.str(), count);
    }
  };
  auto handler = std::make_unique<StorageCompletionHandler>(
      *this, displayName, extension, cache.itemCount);
  if (!ArchiveUtils::saveInBackground(outputFile.str(), attributes,
                                      handler.get()))
    return false; // source-port failure adaptation: keep ownership if not
                  // queued.
  handler
      .release(); // FileIOManager owns successful queued completion handlers.
  return true;
}
bool MixerComponentBase::saveScene(const Core::Portable::FileName &filename,
                                   const char *displayName, bool notify) {
  using namespace Core::Portable;
  if (!saveServices.parameters || !saveServices.inspectCache ||
      !saveServices.saveFlags)
    throw std::logic_error("scene application bindings required");
  if (notify && (!saveServices.completed || !saveServices.cascadePresetStored))
    throw std::logic_error("scene completion policy required");
  const auto cache = saveServices.inspectCache(filename);
  if (cache.found) {
    if (cache.itemCount <= 0)
      return false;
    if (!saveServices.refreshCache)
      throw std::logic_error("cache refresh policy required");
    if (!cache.obsoleteFile.isEmpty() &&
        std::strcmp(cache.obsoleteFile.str(), filename.str()) != 0)
      FileUtils::deleteFile(cache.obsoleteFile.str());
    saveServices.refreshCache(cache);
  }
  const int flags = saveServices.saveFlags(0, nullptr);
  if (flags != 0 && !saveServices.configureStorage)
    throw std::logic_error("scene storage flags adaptation required");
  const auto outputFile = findLocalFile(filename.str());
  class CompletionHandler final : public FileIOCompletionHandler {
    MixerComponentBase &owner;
    FileName directory;
    int count;

  public:
    CompletionHandler(MixerComponentBase &owner, const FileName &directory,
                      int count)
        : owner(owner), directory(directory), count(count) {}
    ~CompletionHandler() override = default;
    void onSaveFileCompleted(Core::CStringPtr filename) override {
      owner.presetSaved(FileName(filename), directory.str(), "scene", count);
      owner.saveServices.cascadePresetStored("scene", count);
    }
  };
  class SaveSceneTask final : public BackgroundTask {
    MixerComponentBase &owner;
    FileName filename;
    int flags;

  public:
    SaveSceneTask(MixerComponentBase &owner, const FileName &filename,
                  int flags)
        : owner(owner), filename(filename), flags(flags) {}
    void work() override {
      Attributes attributes(AttributeAllocator::getDefault());
      AttributesBuilder builder(attributes);
      OutputStorage storage(builder);
      if (owner.saveServices.configureStorage)
        owner.saveServices.configureStorage(storage, flags);
      else if (flags != 0)
        throw std::logic_error("scene storage flags adaptation required");
      owner.saveServices.parameters->save(storage);
      ArchiveUtils::saveToFile(filename.str(), attributes);
    }
  };
  // displayName belongs to the original interface; scene notification uses the
  // cache directory and native literal "scene", as observed in its handler.
  (void)displayName;
  std::unique_ptr<CompletionHandler> handler;
  if (notify)
    handler = std::make_unique<CompletionHandler>(*this, cache.directory,
                                                  cache.itemCount);
  auto task = std::make_unique<SaveSceneTask>(*this, outputFile, flags);
  FileIOManager::instance().addExternalTask(task.get(), outputFile.str(),
                                            handler.get(), true);
  task.release();
  handler.release();
  return true;
}
} // namespace Presonus::Mixer
