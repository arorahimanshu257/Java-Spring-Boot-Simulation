package com.example.project.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.FutureOrPresent;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.time.LocalDateTime;

@Data
public class ReleaseRequestDTO {
    @NotBlank
    @Size(max = 100)
    @Schema(description = "Release version", example = "v1.0.0")
    private String version;

    @Size(max = 255)
    @Schema(description = "Release description", example = "First major release")
    private String description;

    @NotNull
    @FutureOrPresent
    @Schema(description = "Release date", example = "2024-11-01T10:00:00")
    private LocalDateTime releaseDate;
}
