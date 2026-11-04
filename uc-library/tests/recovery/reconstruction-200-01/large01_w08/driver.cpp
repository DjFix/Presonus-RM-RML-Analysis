#include "presonus/mixer/setup_property_applications.hpp"
#include <iostream>
#include <stdexcept>
template <class T> struct TestApp : T {
  using T::T;
  void onProgress(const char *, float) override {
    throw std::runtime_error("unexpected");
  }
  bool isNetworkClientReady() const override {
    throw std::runtime_error("unexpected");
  }
  Presonus::UC::ClientRootComponent *
  createClientComponent(const Presonus::UC::NetworkItem &) override {
    throw std::runtime_error("unexpected");
  }
  void releaseClientComponent(Presonus::UC::ClientRootComponent *) override {
    throw std::runtime_error("unexpected");
  }
};
int main() {
  presonus::mixer::SetupContext ctx({nullptr}, {nullptr});
  {
    TestApp<Presonus::Mixer::StormApplication> a(
        presonus::mixer::setupContextTag, ctx);
    auto v = a.getAudioEngineSetupProperty();
    for (auto w : v.observedWords)
      std::cout << w << " ";
    std::cout << "\n";
  }
  {
    TestApp<Presonus::Mixer::RogueApplication> a(
        presonus::mixer::setupContextTag, ctx);
    unsigned short p = 123;
    Presonus::UC::ServerInfo info;
    info.strings = {"old0", "keep1", "old2", "keep3"};
    info.flags = 123;
    a.getNetworkSetup(p, info);
    if (info.flags != 123 || std::string(info.strings[1]) != "keep1" ||
        std::string(info.strings[3]) != "keep3")
      return 3;
    std::cout << p << "|" << info.strings[0] << "|" << info.strings[2] << "\n";
  }
  {
    TestApp<Presonus::Mixer::StormApplication> a(
        presonus::mixer::setupContextTag, ctx);
    unsigned short p = 123;
    Presonus::UC::ServerInfo info;
    info.strings = {"old0", "keep1", "old2", "keep3"};
    info.flags = 123;
    a.getNetworkSetup(p, info);
    if (info.flags != 123 || std::string(info.strings[1]) != "keep1" ||
        std::string(info.strings[3]) != "keep3")
      return 3;
    std::cout << p << "|" << info.strings[0] << "|" << info.strings[2] << "\n";
  }
  {
    TestApp<Presonus::Mixer::RogueApplication> a(
        presonus::mixer::setupContextTag, ctx);
    auto v = a.getAudioEngineSetupProperty();
    for (auto w : v.observedWords)
      std::cout << w << " ";
    std::cout << "\n";
  }
  {
    TestApp<Presonus::Mixer::WolverineApplication> a(
        presonus::mixer::setupContextTag, ctx);
    unsigned short p = 123;
    Presonus::UC::ServerInfo info;
    info.strings = {"old0", "keep1", "old2", "keep3"};
    info.flags = 123;
    a.getNetworkSetup(p, info);
    if (info.flags != 123 || std::string(info.strings[1]) != "keep1" ||
        std::string(info.strings[3]) != "keep3")
      return 3;
    std::cout << p << "|" << info.strings[0] << "|" << info.strings[2] << "\n";
  }
  {
    TestApp<Presonus::Mixer::GambitApplication> a(
        presonus::mixer::setupContextTag, ctx);
    auto v = a.getAudioEngineSetupProperty();
    for (auto w : v.observedWords)
      std::cout << w << " ";
    std::cout << "\n";
  }
  {
    TestApp<Presonus::Mixer::BeastApplication> a(
        presonus::mixer::setupContextTag, ctx);
    unsigned short p = 123;
    Presonus::UC::ServerInfo info;
    info.strings = {"old0", "keep1", "old2", "keep3"};
    info.flags = 123;
    a.getNetworkSetup(p, info);
    if (info.flags != 123 || std::string(info.strings[1]) != "keep1" ||
        std::string(info.strings[3]) != "keep3")
      return 3;
    std::cout << p << "|" << info.strings[0] << "|" << info.strings[2] << "\n";
  }
  {
    TestApp<Presonus::Mixer::GambitApplication> a(
        presonus::mixer::setupContextTag, ctx);
    unsigned short p = 123;
    Presonus::UC::ServerInfo info;
    info.strings = {"old0", "keep1", "old2", "keep3"};
    info.flags = 123;
    a.getNetworkSetup(p, info);
    if (info.flags != 123 || std::string(info.strings[1]) != "keep1" ||
        std::string(info.strings[3]) != "keep3")
      return 3;
    std::cout << p << "|" << info.strings[0] << "|" << info.strings[2] << "\n";
  }
  {
    TestApp<Presonus::Mixer::WolverineApplication> a(
        presonus::mixer::setupContextTag, ctx);
    auto v = a.getAudioEngineSetupProperty();
    for (auto w : v.observedWords)
      std::cout << w << " ";
    std::cout << "\n";
  }
  {
    TestApp<Presonus::Mixer::BeastApplication> a(
        presonus::mixer::setupContextTag, ctx);
    auto v = a.getAudioEngineSetupProperty();
    for (auto w : v.observedWords)
      std::cout << w << " ";
    std::cout << "\n";
  }
}
