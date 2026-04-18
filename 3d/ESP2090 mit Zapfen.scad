// --- PARAMETER ---
width = 116;          
depth = 76;           
height = 8;           
outer_radius = 1;     
wall_thickness = 2.0; 

// Boden-Öffnungen
bottom_opening_w = 88;
bottom_opening_d = 68;
inner_step_w = 90.5;
inner_step_d = 70.5;
step_height = 2;      

// Zapfen (Pins)
pin_dia = 3.1;
pin_dist_w = 100; 
pin_dist_d = 60;  
pin_extra_height = 3.2; 
pin_total_h = height + pin_extra_height;

// Stabilitäts-Konus (unten)
conus_base_dia = 8.0;  
conus_height = 5.0;    

// Verjüngung Spitze (oben)
tip_taper_h = 1.5;     
tip_taper_dia = 2.0;   

// Befestigungslaschen (Viertelkreise)
tab_radius = 4.5;
tab_height = 2;
hole_dia = 2.00; 

// ZIEL-ABSTÄNDE DER LÖCHER (Mittelpunkt zu Mittelpunkt)
target_dist_x = 86;
target_dist_y = 66;

$fn = 64;             

// Hilfsmodul für die abgerundete Grundform
module rounded_box(w, d, h, r) {
    hull() {
        translate([r, r, 0]) cylinder(h=h, r=r);
        translate([w - r, r, 0]) cylinder(h=h, r=r);
        translate([r, d - r, 0]) cylinder(h=h, r=r);
        translate([w - r, d - r, 0]) cylinder(h=h, r=r);
    }
}

// --- MODELLIERUNG ---
difference() {
    union() {
        // 1. DIE SCHALE
        difference() {
            rounded_box(width, depth, height, outer_radius);
            
            translate([wall_thickness, wall_thickness, wall_thickness])
                rounded_box(width - 2*wall_thickness, 
                            depth - 2*wall_thickness, 
                            height, 
                            max(0.1, outer_radius - wall_thickness));

            translate([(width - bottom_opening_w)/2, (depth - bottom_opening_d)/2, -0.1])
                cube([bottom_opening_w, bottom_opening_d, wall_thickness + 0.2]);
                
            translate([(width - inner_step_w)/2, (depth - inner_step_d)/2, step_height])
                cube([inner_step_w, inner_step_d, height]);
        }

        // 2. DIE VIER ZAPFEN
        start_x_pins = (width - pin_dist_w) / 2;
        start_y_pins = (depth - pin_dist_d) / 2;

        for (x = [0, pin_dist_w]) {
            for (y = [0, pin_dist_d]) {
                translate([start_x_pins + x, start_y_pins + y, 0]) {
                    cylinder(h = pin_total_h - tip_taper_h, d = pin_dia);
                    translate([0, 0, pin_total_h - tip_taper_h])
                        cylinder(h = tip_taper_h, d1 = pin_dia, d2 = tip_taper_dia);
                    translate([0, 0, wall_thickness])
                        cylinder(h = conus_height, d1 = conus_base_dia, d2 = pin_dia);
                }
            }
        }

        // 3. DIE LASCHEN (Viertelkreise)
        edge_x = (width - bottom_opening_w) / 2;
        edge_y = (depth - bottom_opening_d) / 2;

        for (tx = [0, bottom_opening_w]) {
            for (ty = [0, bottom_opening_d]) {
                angle = (tx == 0 && ty == 0) ? 0 : 
                        (tx > 0 && ty == 0) ? 90 : 
                        (tx > 0 && ty > 0) ? 180 : 270;
                translate([edge_x + tx, edge_y + ty, 0])
                    rotate([0, 0, angle])
                    intersection() {
                        cylinder(h = tab_height, r = tab_radius);
                        cube([tab_radius, tab_radius, tab_height]);
                    }
            }
        }
    }

    // 4. ABZUG DER LÖCHER (Exakt 86x66mm)
    // Wir platzieren die Löcher relativ zum Bauteilmittelpunkt
    center_x = width / 2;
    center_y = depth / 2;

    for (lx = [-target_dist_x/2, target_dist_x/2]) {
        for (ly = [-target_dist_y/2, target_dist_y/2]) {
            translate([center_x + lx, center_y + ly, -1]) 
                cylinder(h = tab_height + 2, d = hole_dia);
        }
    }
}
