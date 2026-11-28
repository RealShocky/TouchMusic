#include "Network.h"
#include "public.sdk/source/vst/vstsinglecomponenteffect.h"
#include "public.sdk/source/main/pluginfactory.h"
#include "pluginterfaces/vst/ivstparameterchanges.h"
#include "pluginterfaces/vst/ivstprocesscontext.h"
#include "base/source/fstreamer.h"
#include <algorithm>
#include <cstring>

using namespace Steinberg;
using namespace Steinberg::Vst;
static const FUID bridgeUID(0xA92E35C4, 0xB9D84726, 0x90256C34, 0x7A10D5F2);

class ControlBridge final : public SingleComponentEffect {
public:
    static FUnknown* create(void*) { return static_cast<IAudioProcessor*>(new ControlBridge); }
    tresult PLUGIN_API initialize(FUnknown* context) override {
        auto result = SingleComponentEffect::initialize(context);
        if (result != kResultOk) return result;
        addAudioInput(STR16("Input"), SpeakerArr::kStereo);
        addAudioOutput(STR16("Output"), SpeakerArr::kStereo);
        const TChar* names[] = {STR16("Reverb"), STR16("Delay"), STR16("Robot"), STR16("Pitch"),
            STR16("Tune strength"), STR16("Master"), STR16("Formant"), STR16("Voice slot"),
            STR16("Chord"), STR16("Bridge bypass")};
        for (ParamID id = 0; id < 10; ++id) {
            const int steps = id == 7 ? 4 : id == 8 ? 6 : id == 9 ? 1 : 0;
            parameters.addParameter(names[id], nullptr, steps, network.values[id].load(),
                                    ParameterInfo::kCanAutomate | (id == 9 ? ParameterInfo::kIsBypass : 0), id);
        }
        processContextRequirements.needTempo().needProjectTimeMusic().needTransportState();
        return kResultOk;
    }
    tresult PLUGIN_API setActive(TBool state) override {
        if (state) network.start(); else network.stop();
        return SingleComponentEffect::setActive(state);
    }
    tresult PLUGIN_API terminate() override {
        network.stop();
        return SingleComponentEffect::terminate();
    }
    tresult PLUGIN_API setParamNormalized(ParamID id, ParamValue value) override {
        if (id >= 10 || !std::isfinite(value)) return kInvalidArgument;
        network.values[id].store(std::clamp(value, 0., 1.));
        return SingleComponentEffect::setParamNormalized(id, value);
    }
    tresult PLUGIN_API setBusArrangements(SpeakerArrangement* in, int32 ins,
                                         SpeakerArrangement* out, int32 outs) override {
        if (ins != 1 || outs != 1 || in[0] != out[0]
            || (in[0] != SpeakerArr::kMono && in[0] != SpeakerArr::kStereo)) return kResultFalse;
        return SingleComponentEffect::setBusArrangements(in, ins, out, outs);
    }
    tresult PLUGIN_API canProcessSampleSize(int32 size) override {
        return size == kSample32 || size == kSample64 ? kResultTrue : kResultFalse;
    }
    tresult PLUGIN_API process(ProcessData& data) override {
        if (data.inputParameterChanges) {
            for (int32 index = 0; index < data.inputParameterChanges->getParameterCount(); ++index) {
                auto* queue = data.inputParameterChanges->getParameterData(index);
                if (!queue || queue->getParameterId() >= 10) continue;
                int32 offset = 0; ParamValue value = 0;
                if (queue->getPointCount() && queue->getPoint(queue->getPointCount()-1, offset, value) == kResultTrue
                    && std::isfinite(value)) network.values[queue->getParameterId()].store(std::clamp(value, 0., 1.));
            }
        }
        if (data.processContext) {
            const auto& context = *data.processContext;
            const bool valid = (context.state & ProcessContext::kTempoValid)
                            && (context.state & ProcessContext::kProjectTimeMusicValid);
            network.timingValid.store(valid);
            if (valid && std::isfinite(context.tempo) && std::isfinite(context.projectTimeMusic)) {
                network.tempo.store(context.tempo); network.ppq.store(context.projectTimeMusic);
            }
            network.position.store(static_cast<double>(context.projectTimeSamples));
            network.rate.store(context.sampleRate);
            network.playing.store((context.state & ProcessContext::kPlaying) != 0);
            network.stamp.store(BridgeNetwork::now());
        }
        if (data.numSamples <= 0 || data.numOutputs == 0) return kResultOk;
        for (int32 bus = 0; bus < data.numOutputs; ++bus) {
            auto& output = data.outputs[bus];
            output.silenceFlags = bus < data.numInputs ? data.inputs[bus].silenceFlags : ~uint64(0);
            for (int32 channel = 0; channel < output.numChannels; ++channel) {
                const bool available = bus < data.numInputs && channel < data.inputs[bus].numChannels;
                const size_t bytes = data.numSamples * (data.symbolicSampleSize == kSample64 ? sizeof(double) : sizeof(float));
                void* target = data.symbolicSampleSize == kSample64 ? static_cast<void*>(output.channelBuffers64[channel])
                                                                 : static_cast<void*>(output.channelBuffers32[channel]);
                const void* source = !available ? nullptr : data.symbolicSampleSize == kSample64
                    ? static_cast<void*>(data.inputs[bus].channelBuffers64[channel])
                    : static_cast<void*>(data.inputs[bus].channelBuffers32[channel]);
                if (source) std::memmove(target, source, bytes); else std::memset(target, 0, bytes);
            }
        }
        return kResultOk;
    }
    tresult PLUGIN_API setState(IBStream* stream) override {
        if (!stream) return kInvalidArgument;
        IBStreamer reader(stream, kLittleEndian);
        std::array<double, 10> values;
        for (auto& value : values)
            if (!reader.readDouble(value) || !std::isfinite(value) || value < 0 || value > 1) return kResultFalse;
        for (ParamID index = 0; index < 10; ++index) setParamNormalized(index, values[index]);
        return kResultOk;
    }
    tresult PLUGIN_API getState(IBStream* stream) override {
        if (!stream) return kInvalidArgument;
        IBStreamer writer(stream, kLittleEndian);
        for (auto& value : network.values) if (!writer.writeDouble(value.load())) return kResultFalse;
        return kResultOk;
    }
private:
    BridgeNetwork network;
};

BEGIN_FACTORY_DEF("TouchMusic", "https://github.com/RealShocky/TouchMusic", "")
DEF_CLASS2(INLINE_UID_FROM_FUID(bridgeUID), PClassInfo::kManyInstances, kVstAudioEffectClass,
           "TouchMusic Control Bridge", 0, "Fx|Tools", "0.4.0", kVstVersionString, ControlBridge::create)
END_FACTORY
