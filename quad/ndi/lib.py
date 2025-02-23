import sys
import os.path
import platform

from cffi import FFI

ffi = FFI()

ffi.cdef(r"""
    bool NDIlib_initialize(void);

    typedef struct
    {
        bool show_local_sources;
        const char* p_groups;
        const char* p_extra_ips;
    } NDIlib_find_create_t;

    typedef struct
    {
        const char* p_ndi_name;
        const char* p_url_address;
    } NDIlib_source_t;

    typedef void* NDIlib_find_instance_t;

    // Find functions
    void* NDIlib_find_create_v2(NDIlib_find_create_t* p_create_settings);
    bool NDIlib_find_wait_for_sources(NDIlib_find_instance_t p_instance, uint32_t timeout_in_ms);
    const NDIlib_source_t* NDIlib_find_get_current_sources(NDIlib_find_instance_t p_instance, uint32_t* p_no_sources);

    void NDIlib_find_destroy(NDIlib_find_instance_t p_instance);



    typedef void* NDIlib_recv_instance_t;
    typedef uint32_t NDIlib_recv_color_format_e;
    typedef int32_t NDIlib_recv_bandwidth_e;
    typedef uint32_t NDIlib_FourCC_type_e;
    typedef uint32_t NDIlib_frame_format_type_e;
    typedef uint32_t NDIlib_frame_type_e;

    typedef struct
    {
	    NDIlib_source_t source_to_connect_to;
        NDIlib_recv_color_format_e color_format;
        NDIlib_recv_bandwidth_e bandwidth;
        bool allow_video_fields;
        const char* p_ndi_recv_name;
    } NDIlib_recv_create_v3_t;

    // This describes a video frame
    typedef struct
    {	// The resolution of this frame
        int xres, yres;

        // What FourCC this is with. This can be two values
        NDIlib_FourCC_type_e FourCC;

        // What is the frame-rate of this frame.
        // For instance NTSC is 30000,1001 = 30000/1001 = 29.97fps
        int frame_rate_N, frame_rate_D;

        // What is the picture aspect ratio of this frame.
        // For instance 16.0/9.0 = 1.778 is 16:9 video
        // 0 means square pixels
        float picture_aspect_ratio;

        // Is this a fielded frame, or is it progressive
        NDIlib_frame_format_type_e frame_format_type;

        // The timecode of this frame in 100ns intervals
        int64_t timecode;

        // The video data itself
        uint8_t* p_data;

        // The inter line stride of the video data, in bytes. If the stride is 0
        // then it is sizeof(one pixel)*xres.  If the FourCC is one of the
        // compressed formats, then this is expected to be the size in bytes of
        // the entire buffer.
        int line_stride_in_bytes;

        // Per frame metadata for this frame. This is a NULL terminated UTF8 string that should be
        // in XML format. If you do not want any metadata then you may specify NULL here.
        const char* p_metadata; // Present in >= v2.5

        // This is only valid when receiving a frame and is specified as a 100ns time that was the exact
        // moment that the frame was submitted by the sending side and is generated by the SDK. If this
        // value is NDIlib_recv_timestamp_undefined then this value is not available and is NDIlib_recv_timestamp_undefined.
        int64_t timestamp; // Present in >= v2.5
    } NDIlib_video_frame_v2_t;

    // This describes an audio frame
    typedef struct
    {	// The sample-rate of this buffer
        int sample_rate;

        int no_channels; // The number of audio channels
        int no_samples; // The number of audio samples per channel

        // The timecode of this frame in 100ns intervals
        int64_t timecode;

        float* p_data; // The audio data
        int channel_stride_in_bytes;

        // Per frame metadata for this frame. This is a NULL terminated UTF8 string that should be
        // in XML format. If you do not want any metadata then you may specify NULL here.
        const char* p_metadata; // Present in >= v2.5

        // This is only valid when receiving a frame and is specified as a 100ns time that was the exact
        // moment that the frame was submitted by the sending side and is generated by the SDK. If this
        // value is NDIlib_recv_timestamp_undefined then this value is not available and is NDIlib_recv_timestamp_undefined.
        int64_t timestamp; // Present in >= v2.5
    } NDIlib_audio_frame_v2_t;

    // The data description for metadata
    typedef struct
    {	// The length of the string in UTF8 characters. This includes the NULL terminating character.
        // If this is 0, then the length is assume to be the length of a NULL terminated string.
        int length;

        // The timecode of this frame in 100ns intervals
        int64_t timecode;

        // The metadata as a UTF8 XML string. This is a NULL terminated string.
        char* p_data;
    } NDIlib_metadata_frame_t;

    // Receive functions
    NDIlib_recv_instance_t NDIlib_recv_create_v3(const NDIlib_recv_create_v3_t* p_create_settings);
    void NDIlib_recv_connect(NDIlib_recv_instance_t p_instance, const NDIlib_source_t* p_src);
    NDIlib_frame_type_e NDIlib_recv_capture_v2(
	    NDIlib_recv_instance_t p_instance,      // The library instance
	    NDIlib_video_frame_v2_t* p_video_data,  // The video data received (can be NULL)
	    NDIlib_audio_frame_v2_t* p_audio_data,  // The audio data received (can be NULL)
	    NDIlib_metadata_frame_t* p_metadata,    // The metadata received (can be NULL)
	    uint32_t timeout_in_ms);

    // Receive functions (free)
    void NDIlib_recv_destroy(NDIlib_recv_instance_t p_instance);
    void NDIlib_recv_free_video_v2(NDIlib_recv_instance_t p_instance, const NDIlib_video_frame_v2_t* p_video_data);
    void NDIlib_recv_free_audio_v2(NDIlib_recv_instance_t p_instance, const NDIlib_audio_frame_v2_t* p_audio_data);
    void NDIlib_recv_free_metadata(NDIlib_recv_instance_t p_instance, const NDIlib_metadata_frame_t* p_metadata);

""")

basedir = os.path.dirname(__file__)
uname = platform.uname()
system = uname[0].lower()
machine = uname[4]

if system == 'linux':
    lib = ffi.dlopen(os.path.join(basedir, "bin", f"libndi.{system}.{machine}.so"))
elif (system == 'darwin'):
    lib = ffi.dlopen(os.path.join(basedir, "bin", f"libndi.{system}.{machine}.dylib"))
else: 
    arch = 'x64' if sys.maxsize > 2**32 else 'x86'
    lib = ffi.dlopen(os.path.join(basedir, "bin", f"Processing.NDI.Lib.{arch}.dll"))

if not lib.NDIlib_initialize():
    print("Failed to initialized NDI")

print("NDI Lib initialized")
