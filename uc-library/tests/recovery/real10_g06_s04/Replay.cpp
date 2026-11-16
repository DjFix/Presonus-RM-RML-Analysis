#include "core/portable/corepersistence.h"
#include "presonus/mixer/GlobalComponent.hpp"
#include <cstring>
#include <filesystem>
#include <iostream>
#include <thread>
struct Provider : Core::Portable::Component {
  void add(Core::Portable::Parameter *p) { paramList.add(p); }
  bool result = true;
  int calls = 0;
  bool save(Core::Portable::OutputStorage &s) const override {
    ++const_cast<Provider *>(this)->calls;
    Core::Portable::Component::save(s);
    return result;
  }
};
struct Filter : Core::Portable::IStorageFilter {
  void *castTo(int) override { return nullptr; }
  bool shouldLoad(int, const char *, void *) const override { return true; }
  bool shouldSave(int, const char *, void *) const override { return false; }
};
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  int fil, res, index = 0;
  while (std::cin >> fil >> res) {
    using namespace Core::Portable;
    const auto directory =
        std::filesystem::path(argv[1]) / std::to_string(index++);
    std::filesystem::create_directories(directory);
    Presonus::Mixer::MixerComponentBase mixer;
    mixer.applicationDataRoot = directory.c_str();
    mixer.deviceDataFolder = "bounded";
    Provider provider;
    provider.result = res;
    ParamInfo info{};
    info.type = ParamInfo::kFloat;
    std::strcpy(info.name, "gain");
    info.minValue = 0;
    info.maxValue = 100;
    info.defaultValue = 4.5f;
    info.flags = ParamInfo::kStorable;
    provider.add(new NumericParam(info));
    Filter filter;
    Presonus::Mixer::GlobalComponent global;
    global.bindMixer(mixer);
    global.bindMixerStorage(provider);
    global.storeMixerState(fil ? &filter : nullptr);
    auto &manager = FileIOManager::instance();
    const auto path = global.getTempFilePath();
    Attributes loaded(AttributeAllocator::getDefault());
    bool ok = false;
    for (int i = 0; i < 500 && !ok; ++i) {
      manager.idle();
      if (std::filesystem::exists(path.str()))
        ok = ArchiveUtils::loadFromFile(loaded, path.str());
      if (!ok)
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
    std::cout << "ROW " << provider.calls << ' ' << ok << ' '
              << manager.hasTasks() << ' '
              << std::filesystem::file_size(path.str()) << '\n';
  }
  Core::Portable::FileIOManager::instance().terminate();
}
