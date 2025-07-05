def maidenhead_to_gcs(locator):

    s_long, ss_long, ex_long, s_lat, ss_lat, ex_lat = (0.0,) * 6

    try:
        # Field
        if ((65 <= ord(locator[0]) <= 82) and (65 <= ord(locator[1]) <= 82)):
            # AA starts at (-90, -180) and RR end at (90, 180). There are in total 18 x 18 = 324 squares.
            # field_length_long = 360/18 = 20 | field_length_lat = 180/18 = 10

            long = -180 + ((ord(locator[0]) - 65) * 20)
            # Latitude is vertical, Longitude is horizontal, the first symbol is for longitude and the second for latitude
            # Length = (90 - (-90)) = 180
            lat = -90 + ((ord(locator[1]) - 65) * 10)
        elif ((97 <= ord(locator[0]) <= 114) and (97 <= ord(locator[1]) <= 114)): # Checking if they are wrongfully in lowercase
            print("The locator seems to be badly formated, the fields are in lowercase, interpreting as uppercase")
            long = -180 + ((ord(locator[0]) - 97) * 20)
            lat = -90 + ((ord(locator[1]) - 97) * 10)

        else:
            # Impossible to retrieve valid coordinates
            print(f"Invalid locator (invalid field): {locator}")
            return -1, 0, 0

        if (len(locator) >= 4):
            # Square
            s_long = float(2 * int(locator[2]))
            s_lat = float(1 * int(locator[3]))

            if (len(locator) >= 6):
                # Subsquare
                if ((97 <= ord(locator[4]) <= 120) and (97 <= ord(locator[5]) <= 120)):
                    # The third set of letters goes from AA to XX The grid set is now 2. There are a total of 24 * 24 = 576 squares.
                    # The ss_length = 2/24 = 0.0833333
                    ss_long = float(2/24 * (ord(locator[4]) - 97))
                    ss_lat = float(1/24 * (ord(locator[5]) - 97))

                elif ((65 <= ord(locator[4]) <= 88) and (65 <= ord(locator[5]) <= 88)):
                    print("The locator seems to be badly formated, the subsquare are in uppercase, interpreting as lowercase")
                    ss_long = float(2/24 * (ord(locator[4]) - 65))
                    ss_lat = float(1/24 * (ord(locator[5]) - 65))

                else:
                    # Impossible to retrieve valid coordinates
                    print(f"Invalid locator (invalid subsquare): {locator}")
                    return -1, 0, 0

                if (len(locator) >= 8):
                    #Extendedsquare
                    ex_long = float (2/480 + (2/240 * int(locator[6])))
                    ex_lat = float (1/480 + (1/240 * int(locator[7])))
                else:
                    ex_long = float(2/48)
                    ex_lat = float(1/48)

            else: # If there isn't subsquare calculate the middle of the square
                 ss_long = 1
                 ss_lat = 0.5

        else: # If there isn't square calculate the middle of the field
            s_long = 10
            s_lat = 5

    except Exception as e:
        print(f"An error occurred while processing locator ({locator}): {e}")
        return -1, 0, 0

    return 0, (lat + s_lat + ss_lat + ex_lat), (long + s_long + ss_long + ex_long)

#def main():
#    locators = ["IO93FT", "IO", "ZZ2343", "io93ft", "io93FT", "RR99XX99", "aa00aa00", "b", "GG52RJ85", "IOT442"]
#    for locator in locators:
#        print(f" locator, val, lat, long {locator}: {maidenhead_to_gcs(locator)}")
#
#if __name__ == '__main__':
#    main()
