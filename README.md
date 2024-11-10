# Buienradar Home Assistant Component

This is a custom component for Home Assistant that integrates with Buienradar to provide accurate and up-to-date precipitation forecasts.

## Features

- Real-time precipitation forecasts for your location.
- Supports custom locations by latitude and longitude.
- Fully configurable through the Home Assistant UI.

## Installation

### Manual Installation

1. Download the latest version of this repository from [GitHub](https://github.com/HiDiHo01/Buienalarm).
2. Extract the `buienradar` folder into your Home Assistant `custom_components` directory:
   ```
   <config>/custom_components/buienradar/
   ```
3. Restart Home Assistant.

### HACS Installation

1. Open HACS in your Home Assistant instance.
2. Search for "Buienradar" in the integrations section.
3. Click "Install" and restart Home Assistant.

## Configuration

### Configuration via UI

1. Go to **Settings** > **Devices & Services**.
2. Click **Add Integration**.
3. Search for **Buienradar** and follow the configuration prompts.

### YAML Configuration (Optional)

Alternatively, you can configure the component using YAML:

```yaml
# Example configuration.yaml entry
buienradar:
  latitude: 52.3676  # Optional, defaults to Home Assistant latitude
  longitude: 4.9041  # Optional, defaults to Home Assistant longitude
  monitored_conditions:
    - precipitation
```

## Entities Provided

This integration creates the following sensor entities:

- `sensor.buienradar_precipitation`
- `sensor.buienradar_temperature`
- `sensor.buienradar_humidity`
- `sensor.buienradar_wind_speed`

## Customization

You can customize how the data is displayed in the Home Assistant UI by using Lovelace cards.

## Troubleshooting

If you encounter issues, check the Home Assistant logs for error messages related to the Buienradar component. You can enable debug logging for detailed information:

```yaml
logger:
  default: warning
  logs:
    custom_components.buienradar: debug
```

## Contributing

Contributions are welcome! If you find bugs or have feature requests, please open an issue or submit a pull request on [GitHub](https://github.com/HiDiHo01/Buienalarm).

## License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/HiDiHo01/Buienalarm/blob/main/LICENSE) file for details.
```

You can copy and paste this into a `README.md` file.
