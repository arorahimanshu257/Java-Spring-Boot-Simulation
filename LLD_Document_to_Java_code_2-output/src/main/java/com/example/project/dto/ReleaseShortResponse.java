package com.example.project.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "Short response for associated releases")
public class ReleaseShortResponse {
    @Schema(description = "Release ID", example = "1")
    private Long id;
    @Schema(description = "Release version", example = "v1.0.0")
    private String version;
}
